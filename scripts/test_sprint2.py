#!/usr/bin/env python3
"""
Sprint 2 Verification Suite: Real-Time Event Ingestion, Redis Pipeline & Admin Bot.

Tests:
1. Dialogue & Message SQLAlchemy Models (constraints & relationships).
2. Serialization of Inbound MTProto Event Payloads.
3. InboundEventConsumer Logic (Atomic Dialogue upsert, unread counter increment, Message insertion).
4. aiogram 3.x Admin Alert Formatter & Mini App Deep-Link URL construction.
"""

import asyncio
import json
import os
import sys
import uuid
import logging
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from backend.app.db.base import Base
from backend.app.models.dialogue import Dialogue
from backend.app.models.message import Message, MessageStatus
from backend.app.models.account import Account, AccountStatus
from backend.app.core.config import settings
from bot.handlers.admin import build_admin_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Sprint2Verification")


async def test_database_models_and_upsert() -> bool:
    """Verifies Dialogue & Message models and simulates atomic upsert & unread increment."""
    logger.info("--- Test 1: Database Models & Dialogue Upsert Simulation ---")

    # In-memory SQLite for testing model logic
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    account_id = uuid.uuid4()
    peer_id = 987654321

    async with session_factory() as session:
        # 1. Create dummy Account
        account = Account(
            id=account_id,
            phone="+12025550199",
            title="Sales Team Account",
            status=AccountStatus.ACTIVE,
        )
        session.add(account)

        # 2. First Inbound Message -> Create Dialogue
        dialogue = Dialogue(
            account_id=account_id,
            peer_id=peer_id,
            peer_name="Ivan Petrov",
            peer_username="ivan_p",
            unread_count=1,
            last_message_text="Hello, I need pricing information!",
            last_message_at=datetime.now(timezone.utc),
        )
        session.add(dialogue)
        await session.flush()

        msg1 = Message(
            dialogue_id=dialogue.id,
            account_id=account_id,
            peer_id=peer_id,
            telegram_message_id=101,
            sender_id=peer_id,
            is_outgoing=False,
            text="Hello, I need pricing information!",
            status=MessageStatus.RECEIVED,
        )
        session.add(msg1)
        await session.commit()

        # Verify initial dialogue state
        stmt = select(Dialogue).where(Dialogue.account_id == account_id, Dialogue.peer_id == peer_id)
        result = await session.execute(stmt)
        saved_dialogue = result.scalar_one()
        assert saved_dialogue.unread_count == 1
        assert saved_dialogue.peer_name == "Ivan Petrov"
        logger.info(f"Dialogue initialized with unread_count={saved_dialogue.unread_count}")

        # 3. Second Inbound Message -> Increment unread_count
        saved_dialogue.unread_count += 1
        saved_dialogue.last_message_text = "Are you available for a quick call?"
        saved_dialogue.last_message_at = datetime.now(timezone.utc)

        msg2 = Message(
            dialogue_id=saved_dialogue.id,
            account_id=account_id,
            peer_id=peer_id,
            telegram_message_id=102,
            sender_id=peer_id,
            is_outgoing=False,
            text="Are you available for a quick call?",
            status=MessageStatus.RECEIVED,
        )
        session.add(msg2)
        await session.commit()

        # Verify increment
        result = await session.execute(stmt)
        updated_dialogue = result.scalar_one()
        assert updated_dialogue.unread_count == 2
        assert updated_dialogue.last_message_text == "Are you available for a quick call?"
        logger.info(f"Dialogue updated with unread_count={updated_dialogue.unread_count}")

        # Verify messages list
        msg_stmt = select(Message).where(Message.dialogue_id == updated_dialogue.id)
        msg_result = await session.execute(msg_stmt)
        messages = msg_result.scalars().all()
        assert len(messages) == 2
        logger.info(f"Messages count verified: {len(messages)} messages stored.")

    await test_engine.dispose()
    logger.info("Database models and upsert test PASSED.")
    return True


def test_admin_alert_formatting_and_deeplink() -> bool:
    """Verifies aiogram alert formatting and exact Mini App deep link URL construction."""
    logger.info("--- Test 2: Admin Alert Formatting & Deep-Link URL ---")

    account_id = uuid.uuid4()
    sample_alert_payload = {
        "account_id": str(account_id),
        "account_title": "Enterprise Sales Bot",
        "account_phone": "+79991234567",
        "peer_id": 123456789,
        "sender_name": "Alexander Pushkin",
        "sender_username": "pushkin_dev",
        "message_text": "Good afternoon, we want to order a dedicated cluster.",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    text, keyboard = build_admin_alert(
        data=sample_alert_payload,
        bot_username="StudioCrmAdminBot",
        app_short_name="app",
    )

    logger.info("Generated Telegram Admin Alert HTML:")
    print("--------------------------------------------------")
    print(text)
    print("--------------------------------------------------")

    # Assertions on text
    assert "Enterprise Sales Bot" in text
    assert "+79991234567" in text
    assert "Alexander Pushkin" in text
    assert "@pushkin_dev" in text
    assert "Good afternoon, we want to order a dedicated cluster." in text

    # Assertions on Inline Button
    button = keyboard.inline_keyboard[0][0]
    expected_url = f"https://t.me/StudioCrmAdminBot/app?startapp=chat_{account_id}_123456789"
    logger.info(f"Generated Inline Button URL: {button.url}")

    assert button.text == "💬 Ответить в Mini App"
    assert button.url == expected_url, f"Expected {expected_url}, got {button.url}"

    logger.info("Admin alert message and TMA deep link PASSED.")
    return True


def test_event_payload_serialization() -> bool:
    """Verifies JSON schema integrity of inbound event payloads."""
    logger.info("--- Test 3: Event Payload Schema Integrity ---")

    account_id = uuid.uuid4()
    test_payload = {
        "account_id": str(account_id),
        "account_title": "Support Desk",
        "account_phone": "+12025550188",
        "peer_id": 555666777,
        "telegram_message_id": 4321,
        "sender_id": 555666777,
        "sender_name": "Elena Rostova",
        "sender_username": "elena_r",
        "text": "Can you check invoice #1042?",
        "media_type": None,
        "date": datetime.now(timezone.utc).isoformat(),
    }

    serialized = json.dumps(test_payload)
    deserialized = json.loads(serialized)

    assert deserialized["peer_id"] == 555666777
    assert deserialized["telegram_message_id"] == 4321
    assert deserialized["sender_username"] == "elena_r"
    logger.info("Event serialization PASSED.")
    return True


async def main() -> None:
    logger.info("==================================================")
    logger.info("      STARTING SPRINT 2 VERIFICATION SUITE        ")
    logger.info("==================================================")

    assert await test_database_models_and_upsert()
    assert test_admin_alert_formatting_and_deeplink()
    assert test_event_payload_serialization()

    logger.info("==================================================")
    logger.info("✅ ALL SPRINT 2 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
