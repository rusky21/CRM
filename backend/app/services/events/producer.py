import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from redis.asyncio import Redis
from telethon import events
from telethon.tl.types import User, Channel, Chat, DocumentAttributeFilename

logger = logging.getLogger(__name__)

INBOUND_STREAM_KEY = "stream:inbound_events"
MEDIA_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "media_cache")
os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)


def _extract_media_info(event: events.NewMessage.Event) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """Determines media classification and attributes from Telethon message."""
    media_type = None
    filename = None
    size = None

    if event.photo:
        media_type = "photo"
        filename = f"photo_{event.message.id}.jpg"
    elif event.video:
        media_type = "video"
        filename = f"video_{event.message.id}.mp4"
    elif event.voice:
        media_type = "voice"
        filename = f"voice_{event.message.id}.ogg"
    elif event.audio:
        media_type = "audio"
        filename = f"audio_{event.message.id}.mp3"
    elif event.document:
        media_type = "document"
        if event.message.document:
            size = event.message.document.size
            for attr in event.message.document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    filename = attr.file_name
                    break
        if not filename:
            filename = f"doc_{event.message.id}.bin"
    elif event.sticker:
        media_type = "sticker"

    return media_type, filename, size


async def cache_media_locally(event: events.NewMessage.Event) -> Optional[str]:
    """Downloads incoming media to local cache directory for static serving."""
    if not (event.photo or event.document or event.video or event.voice or event.audio):
        return None

    try:
        media_type, fname, _ = _extract_media_info(event)
        safe_fname = f"{event.message.id}_{fname or 'file.bin'}"
        dest_path = os.path.join(MEDIA_CACHE_DIR, safe_fname)

        if not os.path.exists(dest_path):
            await event.download_media(file=dest_path)

        # Return public web URL mounted in FastAPI
        return f"/media/{safe_fname}"
    except Exception as exc:
        logger.warning(f"Could not download media for msg {event.message.id}: {exc}")
        return None


async def extract_event_payload(
    account_id: UUID,
    event: events.NewMessage.Event,
    account_title: str = "Telegram Account",
    account_phone: str = "",
) -> Dict[str, Any]:
    peer_id = event.chat_id or (event.peer_id.user_id if hasattr(event.peer_id, "user_id") else 0)
    telegram_msg_id = event.message.id
    sender_id = event.sender_id or peer_id

    sender_name = "Unknown"
    sender_username = None

    try:
        sender = await event.get_sender()
        if isinstance(sender, User):
            first = sender.first_name or ""
            last = sender.last_name or ""
            sender_name = f"{first} {last}".strip() or sender.username or f"User {sender.id}"
            sender_username = sender.username
        elif isinstance(sender, (Channel, Chat)):
            sender_name = sender.title or f"Chat {sender.id}"
            sender_username = getattr(sender, "username", None)
    except Exception as exc:
        logger.warning(f"Could not fetch full sender info for event {telegram_msg_id}: {exc}")

    text = event.raw_text or event.message.message or ""
    media_type, filename, size = _extract_media_info(event)
    media_url = await cache_media_locally(event)

    msg_date = event.message.date
    if msg_date and not msg_date.tzinfo:
        msg_date = msg_date.replace(tzinfo=timezone.utc)
    date_iso = msg_date.isoformat() if msg_date else datetime.now(timezone.utc).isoformat()

    return {
        "event_type": "new_message",
        "account_id": str(account_id),
        "account_title": account_title,
        "account_phone": account_phone,
        "peer_id": peer_id,
        "telegram_message_id": telegram_msg_id,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "sender_username": sender_username,
        "text": text,
        "media_type": media_type,
        "media_url": media_url,
        "media_filename": filename,
        "media_size": size,
        "date": date_iso,
    }


async def produce_inbound_event(
    redis_client: Redis,
    account_id: UUID,
    event: events.NewMessage.Event,
    account_title: str = "Telegram Account",
    account_phone: str = "",
) -> Optional[str]:
    """Serializes incoming message and appends to Redis Stream."""
    if event.out:
        return None

    try:
        payload = await extract_event_payload(
            account_id=account_id,
            event=event,
            account_title=account_title,
            account_phone=account_phone,
        )

        stream_entry_id = await redis_client.xadd(
            name=INBOUND_STREAM_KEY,
            fields={"payload": json.dumps(payload, ensure_ascii=False)},
        )
        return stream_entry_id.decode("utf-8") if isinstance(stream_entry_id, bytes) else str(stream_entry_id)

    except Exception as exc:
        logger.error(f"Failed to produce inbound event to Redis: {exc}", exc_info=True)
        return None


async def produce_inbound_edit_event(
    redis_client: Redis,
    account_id: UUID,
    event: events.MessageEdited.Event,
) -> None:
    """Queues message edited event into Redis Stream."""
    peer_id = event.chat_id or (event.peer_id.user_id if hasattr(event.peer_id, "user_id") else 0)
    payload = {
        "event_type": "message_edited",
        "account_id": str(account_id),
        "peer_id": peer_id,
        "telegram_message_id": event.message.id,
        "new_text": event.raw_text or event.message.message or "",
        "date": datetime.now(timezone.utc).isoformat(),
    }
    await redis_client.xadd(INBOUND_STREAM_KEY, {"payload": json.dumps(payload, ensure_ascii=False)})


async def produce_inbound_delete_event(
    redis_client: Redis,
    account_id: UUID,
    deleted_ids: List[int],
    peer_id: Optional[int],
) -> None:
    """Queues message deleted event into Redis Stream."""
    payload = {
        "event_type": "messages_deleted",
        "account_id": str(account_id),
        "peer_id": peer_id,
        "deleted_ids": deleted_ids,
        "date": datetime.now(timezone.utc).isoformat(),
    }
    await redis_client.xadd(INBOUND_STREAM_KEY, {"payload": json.dumps(payload, ensure_ascii=False)})


async def produce_user_typing_event(
    redis_client: Redis,
    account_id: UUID,
    user_id: int,
    action: str = "typing",
) -> None:
    """Publishes live typing update directly to Redis Pub/Sub for active chats."""
    channel = f"channel:chat:{account_id}:{user_id}"
    payload = {
        "type": "user_typing",
        "account_id": str(account_id),
        "peer_id": user_id,
        "action": action,
    }
    await redis_client.publish(channel, json.dumps(payload))
