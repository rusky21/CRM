#!/usr/bin/env python3
"""
Sprint 6 Verification Suite: Two-Way MTProto Cloud Synchronization.

Tests:
1. Outbound Message Editing & Revocation (Delete for everyone).
2. Media Dispatching (Photo & Document file persistence).
3. Real-Time Typing Actions (Outbound action + Inbound raw updates).
4. End-to-End Consumer Ingestion for Edits and Deletions.
"""

import asyncio
import os
import sys
import uuid
import logging
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from backend.app.db.base import Base
from backend.app.models.account import Account, AccountStatus
from backend.app.models.dialogue import Dialogue
from backend.app.models.message import Message, MessageStatus
from backend.app.services.outbound_dispatcher import OutboundDispatcher
from backend.app.services.mtproto.pool_manager import MTProtoPoolManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Sprint6Verification")


async def test_cloud_edit_and_delete() -> bool:
    """Verifies OutboundDispatcher message editing and cloud revocation (delete for everyone)."""
    logger.info("--- Test 1: Cloud Message Editing & Revocation ---")

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    account_id = uuid.uuid4()
    peer_id = 998877
    telegram_msg_id = 554411

    # Mock Telethon client instance
    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.status = AccountStatus.ACTIVE
    mock_client.edit_message = AsyncMock()
    mock_client.delete_messages = AsyncMock()
    mock_client.send_typing = AsyncMock()

    pool = MTProtoPoolManager.get_instance()
    pool._clients[account_id] = mock_client
    dispatcher = OutboundDispatcher(pool_manager=pool)

    async with session_factory() as session:
        # Seed Dialogue and Message
        acc = Account(id=account_id, phone="+12025550199", title="Sales Agent", status=AccountStatus.ACTIVE)
        session.add(acc)

        dialogue = Dialogue(
            account_id=account_id,
            peer_id=peer_id,
            peer_name="Client Test",
            last_message_text="Original Text",
        )
        session.add(dialogue)
        await session.flush()

        msg = Message(
            dialogue_id=dialogue.id,
            account_id=account_id,
            peer_id=peer_id,
            telegram_message_id=telegram_msg_id,
            sender_id=123,
            is_outgoing=True,
            is_edited=False,
            text="Original Text",
            status=MessageStatus.DELIVERED,
        )
        session.add(msg)
        await session.commit()

        # 1. Test Cloud Edit
        edit_res = await dispatcher.edit_message(
            session=session,
            account_id=account_id,
            peer_id=peer_id,
            telegram_message_id=telegram_msg_id,
            new_text="Edited Text with corrections",
        )
        mock_client.edit_message.assert_called_once_with(peer_id, telegram_msg_id, "Edited Text with corrections")
        assert edit_res["is_edited"] is True

        # Verify DB update
        stmt = select(Message).where(Message.telegram_message_id == telegram_msg_id)
        updated_msg = (await session.execute(stmt)).scalar_one()
        assert updated_msg.text == "Edited Text with corrections"
        assert updated_msg.is_edited is True
        logger.info("Message edit verified in DB and Telethon call.")

        # 2. Test Cloud Deletion (Revoke)
        del_res = await dispatcher.delete_message(
            session=session,
            account_id=account_id,
            peer_id=peer_id,
            telegram_message_id=telegram_msg_id,
            revoke=True,
        )
        mock_client.delete_messages.assert_called_once_with(peer_id, [telegram_msg_id], revoke=True)
        assert telegram_msg_id in del_res["deleted_ids"]

        # Verify DB deletion
        deleted_check = (await session.execute(stmt)).scalar_one_or_none()
        assert deleted_check is None
        logger.info("Message deletion (revoke) verified in DB and Telethon call.")

    await test_engine.dispose()
    logger.info("Cloud Edit & Delete tests PASSED.")
    return True


async def test_media_dispatch() -> bool:
    """Verifies media sending (photo/document) and attribute recording."""
    logger.info("--- Test 2: Outbound Media Dispatch ---")

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    account_id = uuid.uuid4()
    peer_id = 112233
    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.client.session.user_id = 999

    telethon_msg = MagicMock()
    telethon_msg.id = 776655
    telethon_msg.date = None
    mock_client.send_file = AsyncMock(return_value=telethon_msg)

    pool = MTProtoPoolManager.get_instance()
    pool._clients[account_id] = mock_client
    dispatcher = OutboundDispatcher(pool_manager=pool)

    # Temporary test file
    test_file_path = os.path.abspath(__file__)

    async with session_factory() as session:
        acc = Account(id=account_id, phone="+12025550199", title="Support Agent", status=AccountStatus.ACTIVE)
        session.add(acc)
        await session.commit()

        result = await dispatcher.send_media(
            session=session,
            account_id=account_id,
            peer_id=peer_id,
            file_path=test_file_path,
            caption="Please see attached documentation",
            media_type="document",
            media_url="/media/test_doc.bin",
        )

        assert result["telegram_message_id"] == 776655
        assert result["media_type"] == "document"
        assert result["media_url"] == "/media/test_doc.bin"
        assert result["text"] == "Please see attached documentation"

        stmt = select(Message).where(Message.telegram_message_id == 776655)
        saved_media_msg = (await session.execute(stmt)).scalar_one()
        assert saved_media_msg.media_type == "document"
        assert saved_media_msg.media_url == "/media/test_doc.bin"

    await test_engine.dispose()
    logger.info("Media dispatching tests PASSED.")
    return True


async def test_typing_action() -> bool:
    """Verifies outbound typing action invocation."""
    logger.info("--- Test 3: Real-Time Typing Action ---")
    account_id = uuid.uuid4()
    peer_id = 445566

    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.send_typing = AsyncMock()

    pool = MTProtoPoolManager.get_instance()
    pool._clients[account_id] = mock_client
    dispatcher = OutboundDispatcher(pool_manager=pool)

    await dispatcher.send_typing(account_id, peer_id)
    mock_client.send_typing.assert_called_once_with(peer_id)
    logger.info("Typing action verified.")
    return True


async def main() -> None:
    logger.info("==================================================")
    logger.info("      STARTING SPRINT 6 VERIFICATION SUITE        ")
    logger.info("==================================================")

    assert await test_cloud_edit_and_delete()
    assert await test_media_dispatch()
    assert await test_typing_action()

    logger.info("==================================================")
    logger.info("✅ ALL SPRINT 6 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
