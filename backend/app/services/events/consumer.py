import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import ResponseError
from sqlalchemy import select, update, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.models.dialogue import Dialogue
from backend.app.models.message import Message, MessageStatus
from backend.app.services.events.producer import INBOUND_STREAM_KEY

logger = logging.getLogger(__name__)

INBOUND_GROUP_NAME = "group:inbound_processors"
ADMIN_ALERTS_CHANNEL = "channel:admin_alerts"
CHAT_CHANNEL_PREFIX = "channel:chat"


class InboundEventConsumer:
    """
    Resilient Redis Stream consumer utilizing consumer groups (XREADGROUP + XACK)
    to ingest incoming MTProto events, message edits, deletions, and real-time broadcasts.
    """

    def __init__(
        self,
        redis_client: Redis,
        session_factory: async_sessionmaker[AsyncSession],
        consumer_name: str = "worker-1",
    ) -> None:
        self.redis = redis_client
        self.session_factory = session_factory
        self.consumer_name = consumer_name
        self.is_running: bool = False
        self._consumer_task: Optional[asyncio.Task] = None

    async def init_consumer_group(self) -> None:
        try:
            await self.redis.xgroup_create(
                name=INBOUND_STREAM_KEY,
                groupname=INBOUND_GROUP_NAME,
                id="0",
                mkstream=True,
            )
            logger.info(f"Created consumer group {INBOUND_GROUP_NAME} on stream {INBOUND_STREAM_KEY}.")
        except ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                logger.debug(f"Consumer group {INBOUND_GROUP_NAME} already exists.")
            else:
                raise exc

    async def start(self) -> None:
        await self.init_consumer_group()
        self.is_running = True
        self._consumer_task = asyncio.create_task(self._consume_loop())
        logger.info(f"InboundEventConsumer [{self.consumer_name}] started listening.")

    async def stop(self) -> None:
        self.is_running = False
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info(f"InboundEventConsumer [{self.consumer_name}] stopped.")

    async def _consume_loop(self) -> None:
        while self.is_running:
            try:
                streams_data = await self.redis.xreadgroup(
                    groupname=INBOUND_GROUP_NAME,
                    consumername=self.consumer_name,
                    streams={INBOUND_STREAM_KEY: ">"},
                    count=10,
                    block=2000,
                )

                if not streams_data:
                    continue

                for _, entries in streams_data:
                    for entry_id, fields in entries:
                        await self._process_entry(entry_id, fields)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in Redis consume loop: {exc}", exc_info=True)
                await asyncio.sleep(1)

    async def _process_entry(self, entry_id: bytes | str, fields: Dict[bytes, bytes] | Dict[str, str]) -> None:
        entry_str_id = entry_id.decode("utf-8") if isinstance(entry_id, bytes) else str(entry_id)

        try:
            payload_raw = fields.get(b"payload") or fields.get("payload")
            if not payload_raw:
                await self.redis.xack(INBOUND_STREAM_KEY, INBOUND_GROUP_NAME, entry_str_id)
                return

            payload_str = payload_raw.decode("utf-8") if isinstance(payload_raw, bytes) else payload_raw
            data: Dict[str, Any] = json.loads(payload_str)
            event_type = data.get("event_type", "new_message")
            account_id = UUID(data["account_id"])

            if event_type == "new_message":
                await self._handle_new_message(account_id, data)
            elif event_type == "message_edited":
                await self._handle_message_edited(account_id, data)
            elif event_type == "messages_deleted":
                await self._handle_messages_deleted(account_id, data)

            await self.redis.xack(INBOUND_STREAM_KEY, INBOUND_GROUP_NAME, entry_str_id)

        except Exception as exc:
            logger.error(f"Failed processing entry {entry_str_id}: {exc}", exc_info=True)

    async def _handle_new_message(self, account_id: UUID, data: Dict[str, Any]) -> None:
        peer_id = int(data["peer_id"])
        telegram_msg_id = int(data["telegram_message_id"])
        sender_id = int(data["sender_id"])
        sender_name = data.get("sender_name", "Unknown")
        sender_username = data.get("sender_username")
        text = data.get("text") or ""
        media_type = data.get("media_type")
        media_url = data.get("media_url")
        media_filename = data.get("media_filename")
        media_size = data.get("media_size")
        msg_date = datetime.fromisoformat(data["date"])

        async with self.session_factory() as session:
            async with session.begin():
                dialogue_id = await self._upsert_dialogue(
                    session=session,
                    account_id=account_id,
                    peer_id=peer_id,
                    peer_name=sender_name,
                    peer_username=sender_username,
                    last_message_text=text or f"[{media_type or 'Media'}]",
                    last_message_at=msg_date,
                )

                await self._insert_message(
                    session=session,
                    dialogue_id=dialogue_id,
                    account_id=account_id,
                    peer_id=peer_id,
                    telegram_msg_id=telegram_msg_id,
                    sender_id=sender_id,
                    text=text,
                    media_type=media_type,
                    media_url=media_url,
                    media_filename=media_filename,
                    media_size=media_size,
                    created_at=msg_date,
                )

        # Broadcast Admin Alert
        alert_payload = {
            "account_id": str(account_id),
            "account_title": data.get("account_title", "Account"),
            "account_phone": data.get("account_phone", ""),
            "peer_id": peer_id,
            "sender_name": sender_name,
            "sender_username": sender_username,
            "message_text": text or f"[{media_type or 'Media'}]",
            "created_at": data["date"],
        }
        await self.redis.publish(ADMIN_ALERTS_CHANNEL, json.dumps(alert_payload, ensure_ascii=False))

        # Auto-sync lead to existing StudioCRM
        try:
            from backend.app.services.lead_sync import auto_sync_single_lead
            asyncio.create_task(
                auto_sync_single_lead(
                    peer_name=sender_name,
                    peer_username=sender_username,
                    account_title=data.get("account_title"),
                    initial_text=text,
                )
            )
        except Exception as exc:
            logger.debug(f"Lead auto-sync background trigger failed: {exc}")

        # Broadcast to active TMA WebSocket clients
        chat_channel = f"{CHAT_CHANNEL_PREFIX}:{account_id}:{peer_id}"
        chat_payload = {
            "type": "new_message",
            "dialogue_id": str(dialogue_id),
            "account_id": str(account_id),
            "peer_id": peer_id,
            "telegram_message_id": telegram_msg_id,
            "sender_id": sender_id,
            "is_outgoing": False,
            "text": text,
            "media_type": media_type,
            "media_url": media_url,
            "media_filename": media_filename,
            "media_size": media_size,
            "status": MessageStatus.RECEIVED.value,
            "created_at": data["date"],
        }
        await self.redis.publish(chat_channel, json.dumps(chat_payload, ensure_ascii=False))

    async def _handle_message_edited(self, account_id: UUID, data: Dict[str, Any]) -> None:
        peer_id = int(data["peer_id"])
        telegram_msg_id = int(data["telegram_message_id"])
        new_text = str(data["new_text"])

        async with self.session_factory() as session:
            async with session.begin():
                stmt = (
                    update(Message)
                    .where(
                        Message.account_id == account_id,
                        Message.peer_id == peer_id,
                        Message.telegram_message_id == telegram_msg_id,
                    )
                    .values(text=new_text, is_edited=True)
                )
                await session.execute(stmt)

        # Broadcast edit to TMA WebSocket
        chat_channel = f"{CHAT_CHANNEL_PREFIX}:{account_id}:{peer_id}"
        edit_payload = {
            "type": "message_edited",
            "account_id": str(account_id),
            "peer_id": peer_id,
            "telegram_message_id": telegram_msg_id,
            "text": new_text,
            "is_edited": True,
        }
        await self.redis.publish(chat_channel, json.dumps(edit_payload))

    async def _handle_messages_deleted(self, account_id: UUID, data: Dict[str, Any]) -> None:
        peer_id = data.get("peer_id")
        deleted_ids: List[int] = data.get("deleted_ids", [])

        if not deleted_ids:
            return

        async with self.session_factory() as session:
            async with session.begin():
                stmt = delete(Message).where(
                    Message.account_id == account_id,
                    Message.telegram_message_id.in_(deleted_ids),
                )
                await session.execute(stmt)

        # Broadcast deletion to TMA WebSocket
        if peer_id:
            chat_channel = f"{CHAT_CHANNEL_PREFIX}:{account_id}:{peer_id}"
            del_payload = {
                "type": "messages_deleted",
                "account_id": str(account_id),
                "peer_id": peer_id,
                "deleted_ids": deleted_ids,
            }
            await self.redis.publish(chat_channel, json.dumps(del_payload))

    async def _upsert_dialogue(
        self,
        session: AsyncSession,
        account_id: UUID,
        peer_id: int,
        peer_name: str,
        peer_username: Optional[str],
        last_message_text: str,
        last_message_at: datetime,
    ) -> UUID:
        insert_stmt = pg_insert(Dialogue).values(
            account_id=account_id,
            peer_id=peer_id,
            peer_name=peer_name,
            peer_username=peer_username,
            unread_count=1,
            last_message_text=last_message_text,
            last_message_at=last_message_at,
            updated_at=func.now(),
        )

        upsert_stmt = insert_stmt.on_conflict_do_update(
            constraint="uq_dialogues_account_peer",
            set_={
                "unread_count": Dialogue.unread_count + 1,
                "last_message_text": last_message_text,
                "last_message_at": last_message_at,
                "peer_name": peer_name,
                "peer_username": peer_username,
                "updated_at": func.now(),
            },
        ).returning(Dialogue.id)

        result = await session.execute(upsert_stmt)
        return result.scalar_one()

    async def _insert_message(
        self,
        session: AsyncSession,
        dialogue_id: UUID,
        account_id: UUID,
        peer_id: int,
        telegram_msg_id: int,
        sender_id: int,
        text: Optional[str],
        media_type: Optional[str],
        media_url: Optional[str],
        media_filename: Optional[str],
        media_size: Optional[int],
        created_at: datetime,
    ) -> None:
        insert_stmt = pg_insert(Message).values(
            dialogue_id=dialogue_id,
            account_id=account_id,
            peer_id=peer_id,
            telegram_message_id=telegram_msg_id,
            sender_id=sender_id,
            is_outgoing=False,
            is_edited=False,
            text=text,
            media_type=media_type,
            media_url=media_url,
            media_filename=media_filename,
            media_size=media_size,
            status=MessageStatus.RECEIVED,
            created_at=created_at,
        )

        ignore_stmt = insert_stmt.on_conflict_do_nothing(
            constraint="uq_messages_account_peer_telegram_id"
        )
        await session.execute(ignore_stmt)
