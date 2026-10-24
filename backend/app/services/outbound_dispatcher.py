import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.errors import FloodWaitError, PeerFloodError

from backend.app.models.account import Account, AccountStatus
from backend.app.models.dialogue import Dialogue
from backend.app.models.message import Message, MessageStatus
from backend.app.core.circuit_breaker import CircuitBreaker
from backend.app.services.ai.base_hook import BaseAIAutoReplyHook, PassThroughAIHook
from backend.app.services.mtproto.pool_manager import MTProtoPoolManager

logger = logging.getLogger(__name__)


class OutboundDispatcher:
    """
    Coordinates outbound message delivery, cloud edits, deletions, typing status,
    and media dispatches through pooled Telethon MTProto instances.
    """

    def __init__(
        self,
        pool_manager: MTProtoPoolManager,
        ai_hook: Optional[BaseAIAutoReplyHook] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.pool = pool_manager
        self.ai_hook = ai_hook or PassThroughAIHook()
        self.circuit_breaker = circuit_breaker or CircuitBreaker.get_instance()

    def _get_active_client(self, account_id: UUID):
        client = self.pool.get_client(account_id)
        if not client:
            raise ValueError(f"No MTProto client instance found in pool for account {account_id}.")
        if client.status == AccountStatus.BANNED:
            raise PermissionError("ACCOUNT_BANNED_READ_ONLY")
        if not client.is_connected:
            raise ConnectionError(f"MTProto client for account {account_id} is disconnected.")
        return client

    async def send_typing(self, account_id: UUID, peer_id: int) -> None:
        """Dispatches cloud typing action."""
        client = self._get_active_client(account_id)
        await client.send_typing(peer_id)

    async def dispatch(
        self,
        session: AsyncSession,
        account_id: UUID,
        peer_id: int,
        text: str,
        temp_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches outbound text message."""
        is_available, remaining = await self.circuit_breaker.check_account_available(account_id)
        if not is_available:
            raise RuntimeError(f"Account {account_id} is under Telegram FloodWait ({remaining}s remaining).")

        await self.circuit_breaker.enforce_rate_limit(account_id, peer_id, min_interval_seconds=1.0)

        transformed_text = text
        if await self.ai_hook.should_intercept(account_id, peer_id, text):
            transformed_text = await self.ai_hook.process_outbound(account_id, peer_id, text)

        client = self._get_active_client(account_id)

        try:
            telethon_msg = await client.client.send_message(entity=peer_id, message=transformed_text)
            telegram_msg_id = telethon_msg.id
            sent_at = telethon_msg.date
            if sent_at and not sent_at.tzinfo:
                sent_at = sent_at.replace(tzinfo=timezone.utc)
            else:
                sent_at = datetime.now(timezone.utc)
        except FloodWaitError as exc:
            await self.circuit_breaker.record_flood_wait(account_id, exc.seconds, session)
            raise
        except PeerFloodError as exc:
            await self.circuit_breaker.record_peer_flood(account_id, peer_id, session)
            raise

        # Upsert Dialogue
        upsert_dialogue_stmt = (
            pg_insert(Dialogue)
            .values(
                account_id=account_id,
                peer_id=peer_id,
                peer_name=f"User {peer_id}",
                unread_count=0,
                last_message_text=transformed_text,
                last_message_at=sent_at,
                updated_at=func.now(),
            )
            .on_conflict_do_update(
                constraint="uq_dialogues_account_peer",
                set_={
                    "last_message_text": transformed_text,
                    "last_message_at": sent_at,
                    "updated_at": func.now(),
                },
            )
            .returning(Dialogue.id)
        )
        dialogue_res = await session.execute(upsert_dialogue_stmt)
        dialogue_id = dialogue_res.scalar_one()

        # Insert Message
        insert_msg_stmt = (
            pg_insert(Message)
            .values(
                dialogue_id=dialogue_id,
                account_id=account_id,
                peer_id=peer_id,
                telegram_message_id=telegram_msg_id,
                sender_id=client.client.session.user_id if hasattr(client.client.session, "user_id") else 0,
                is_outgoing=True,
                is_edited=False,
                text=transformed_text,
                status=MessageStatus.DELIVERED,
                created_at=sent_at,
            )
            .returning(Message.id)
        )
        msg_res = await session.execute(insert_msg_stmt)
        message_db_id = msg_res.scalar_one()
        await session.commit()

        return {
            "temp_id": temp_id,
            "message_id": str(message_db_id),
            "dialogue_id": str(dialogue_id),
            "telegram_message_id": telegram_msg_id,
            "account_id": str(account_id),
            "peer_id": peer_id,
            "text": transformed_text,
            "is_outgoing": True,
            "is_edited": False,
            "status": MessageStatus.DELIVERED.value,
            "created_at": sent_at.isoformat(),
        }

    async def edit_message(
        self,
        session: AsyncSession,
        account_id: UUID,
        peer_id: int,
        telegram_message_id: int,
        new_text: str,
    ) -> Dict[str, Any]:
        """Edits an existing message in Telegram cloud and PostgreSQL."""
        client = self._get_active_client(account_id)
        await client.edit_message(peer_id, telegram_message_id, new_text)

        stmt = (
            update(Message)
            .where(
                Message.account_id == account_id,
                Message.peer_id == peer_id,
                Message.telegram_message_id == telegram_message_id,
            )
            .values(text=new_text, is_edited=True)
        )
        await session.execute(stmt)
        await session.commit()

        return {
            "account_id": str(account_id),
            "peer_id": peer_id,
            "telegram_message_id": telegram_message_id,
            "text": new_text,
            "is_edited": True,
        }

    async def delete_message(
        self,
        session: AsyncSession,
        account_id: UUID,
        peer_id: int,
        telegram_message_id: int,
        revoke: bool = True,
    ) -> Dict[str, Any]:
        """Revokes message from Telegram servers and drops from database."""
        client = self._get_active_client(account_id)
        await client.delete_messages(peer_id, [telegram_message_id], revoke=revoke)

        stmt = delete(Message).where(
            Message.account_id == account_id,
            Message.telegram_message_id == telegram_message_id,
        )
        await session.execute(stmt)
        await session.commit()

        return {
            "account_id": str(account_id),
            "peer_id": peer_id,
            "deleted_ids": [telegram_message_id],
        }

    async def send_media(
        self,
        session: AsyncSession,
        account_id: UUID,
        peer_id: int,
        file_path: str,
        caption: Optional[str] = None,
        media_type: str = "photo",
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches photo or document to Telegram cloud via MTProto."""
        client = self._get_active_client(account_id)
        telethon_msg = await client.send_file(peer_id=peer_id, file=file_path, caption=caption)

        telegram_msg_id = telethon_msg.id
        sent_at = telethon_msg.date
        if sent_at and not sent_at.tzinfo:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        else:
            sent_at = datetime.now(timezone.utc)

        # Upsert Dialogue
        upsert_dialogue_stmt = (
            pg_insert(Dialogue)
            .values(
                account_id=account_id,
                peer_id=peer_id,
                peer_name=f"User {peer_id}",
                unread_count=0,
                last_message_text=caption or f"[{media_type.capitalize()}]",
                last_message_at=sent_at,
                updated_at=func.now(),
            )
            .on_conflict_do_update(
                constraint="uq_dialogues_account_peer",
                set_={
                    "last_message_text": caption or f"[{media_type.capitalize()}]",
                    "last_message_at": sent_at,
                    "updated_at": func.now(),
                },
            )
            .returning(Dialogue.id)
        )
        dialogue_res = await session.execute(upsert_dialogue_stmt)
        dialogue_id = dialogue_res.scalar_one()

        # Insert Message
        filename = os.path.basename(file_path)
        size = os.path.getsize(file_path) if os.path.exists(file_path) else None

        insert_msg_stmt = (
            pg_insert(Message)
            .values(
                dialogue_id=dialogue_id,
                account_id=account_id,
                peer_id=peer_id,
                telegram_message_id=telegram_msg_id,
                sender_id=client.client.session.user_id if hasattr(client.client.session, "user_id") else 0,
                is_outgoing=True,
                is_edited=False,
                text=caption,
                media_type=media_type,
                media_url=media_url,
                media_filename=filename,
                media_size=size,
                status=MessageStatus.DELIVERED,
                created_at=sent_at,
            )
            .returning(Message.id)
        )
        msg_res = await session.execute(insert_msg_stmt)
        message_db_id = msg_res.scalar_one()
        await session.commit()

        return {
            "message_id": str(message_db_id),
            "dialogue_id": str(dialogue_id),
            "telegram_message_id": telegram_msg_id,
            "account_id": str(account_id),
            "peer_id": peer_id,
            "text": caption,
            "media_type": media_type,
            "media_url": media_url,
            "media_filename": filename,
            "media_size": size,
            "is_outgoing": True,
            "status": MessageStatus.DELIVERED.value,
            "created_at": sent_at.isoformat(),
        }
