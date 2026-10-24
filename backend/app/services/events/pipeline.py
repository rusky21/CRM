import logging
from typing import List, Optional
from uuid import UUID
from redis.asyncio import Redis
from telethon import events

from backend.app.services.mtproto.pool_manager import MTProtoPoolManager
from backend.app.services.events.producer import (
    produce_inbound_event,
    produce_inbound_edit_event,
    produce_inbound_delete_event,
    produce_user_typing_event,
)

logger = logging.getLogger(__name__)


def attach_inbound_pipeline(
    pool_manager: MTProtoPoolManager,
    redis_client: Redis,
) -> None:
    """
    Connects MTProtoPoolManager to Redis Stream producers for:
    1. Incoming new messages
    2. Message edits
    3. Cloud deletions
    4. Real-time typing indicators
    """

    async def _on_incoming_message(account_id: UUID, event: events.NewMessage.Event) -> None:
        client_instance = pool_manager.get_client(account_id)
        account_title = "Managed Account"
        account_phone = ""
        if client_instance:
            account_phone = client_instance.phone
            account_title = f"Account {client_instance.phone}"

        await produce_inbound_event(
            redis_client=redis_client,
            account_id=account_id,
            event=event,
            account_title=account_title,
            account_phone=account_phone,
        )

    async def _on_message_edited(account_id: UUID, event: events.MessageEdited.Event) -> None:
        await produce_inbound_edit_event(redis_client, account_id, event)

    async def _on_message_deleted(account_id: UUID, deleted_ids: List[int], chat_id: Optional[int]) -> None:
        await produce_inbound_delete_event(redis_client, account_id, deleted_ids, chat_id)

    async def _on_user_typing(account_id: UUID, user_id: int, action: str) -> None:
        await produce_user_typing_event(redis_client, account_id, user_id, action)

    # Register handlers on pool manager
    pool_manager.register_global_message_handler(_on_incoming_message)

    # Attach listeners to existing and future clients
    for client in pool_manager._clients.values():
        client.set_edit_handler(_on_message_edited)
        client.set_delete_handler(_on_message_deleted)
        client.set_typing_handler(_on_user_typing)

    logger.info("Complete two-way MTProto inbound pipeline (messages, edits, deletes, typing) attached.")
