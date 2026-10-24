#!/usr/bin/env python3
"""
Sprint 3 Verification Suite: REST API, TMA Authentication, WebSocket Gateway & Outbound Dispatcher.

Tests:
1. Official Telegram Mini App initData HMAC-SHA256 Cryptographic Validator.
2. Tamper and Expiry Resistance of TMA Auth.
3. Outbound Message Dispatcher with DB commit, temp_id reconciliation, and optimistic delivery.
4. WebSocket Connection Manager chat subscription & broadcast logic.
"""

import asyncio
import hashlib
import hmac
import os
import sys
import time
import uuid
import logging
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from backend.app.db.base import Base
from backend.app.models.account import Account, AccountStatus
from backend.app.models.dialogue import Dialogue
from backend.app.models.message import Message, MessageStatus
from backend.app.core.telegram_auth import parse_and_validate_telegram_init_data
from backend.app.services.outbound_dispatcher import OutboundDispatcher
from backend.app.services.mtproto.pool_manager import MTProtoPoolManager
from backend.app.services.websocket.manager import WebSocketConnectionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Sprint3Verification")


def generate_valid_tma_init_data(bot_token: str, user_id: int = 12345678, auth_date: int = None) -> str:
    """Helper generating authentic Telegram Mini App initData signed with HMAC-SHA256."""
    if auth_date is None:
        auth_date = int(time.time())

    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohD7v23x",
        "user": f'{{"id":{user_id},"first_name":"Alex","username":"alex_tg"}}',
    }

    # Sort keys
    sorted_pairs = sorted(params.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_pairs)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Reconstruct query string
    query_parts = [f"{k}={v}" for k, v in params.items()]
    query_parts.append(f"hash={calculated_hash}")
    return "&".join(query_parts)


def test_tma_init_data_cryptographic_validator() -> bool:
    """Validates Telegram Mini App HMAC-SHA256 signature verification."""
    logger.info("--- Test 1: TMA Cryptographic initData Verification ---")
    dummy_bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"

    # 1. Valid Signature
    valid_init_data = generate_valid_tma_init_data(dummy_bot_token, user_id=999888)
    parsed = parse_and_validate_telegram_init_data(valid_init_data, dummy_bot_token)
    assert parsed["user"]["id"] == 999888
    assert parsed["user"]["username"] == "alex_tg"
    logger.info("Authentic initData successfully verified.")

    # 2. Tampered Payload (modified query_id)
    tampered_init_data = valid_init_data.replace("alex_tg", "hacker_tg")
    try:
        parse_and_validate_telegram_init_data(tampered_init_data, dummy_bot_token)
        logger.error("Tamper check failed: tampered payload was accepted!")
        return False
    except HTTPException as exc:
        assert exc.status_code == 401
        logger.info(f"Tampered initData correctly rejected: {exc.detail}")

    # 3. Expired initData (timestamp 48 hours ago)
    expired_init_data = generate_valid_tma_init_data(dummy_bot_token, auth_date=int(time.time()) - 172800)
    try:
        parse_and_validate_telegram_init_data(expired_init_data, dummy_bot_token, max_age_seconds=86400)
        logger.error("Expiry check failed: expired payload was accepted!")
        return False
    except HTTPException as exc:
        assert exc.status_code == 401
        logger.info(f"Expired initData correctly rejected: {exc.detail}")

    logger.info("TMA initData verification PASSED.")
    return True


async def test_outbound_dispatcher_flow() -> bool:
    """Verifies OutboundDispatcher: Telethon transmission, optimistic temp_id, and DB storage."""
    logger.info("--- Test 2: Outbound Dispatcher Flow & Reconciliation ---")

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    account_id = uuid.uuid4()
    peer_id = 777888999
    temp_id = "client_temp_msg_001"
    outbound_text = "Good day! Your commercial proposal is ready."

    # Mock Telethon client instance
    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.status = AccountStatus.ACTIVE
    mock_client.is_authorized = AsyncMock(return_value=True)

    # Mock Telethon send_message response
    mock_telethon_msg = MagicMock()
    mock_telethon_msg.id = 554433
    mock_telethon_msg.date = None
    mock_client.client.send_message = AsyncMock(return_value=mock_telethon_msg)
    mock_client.client.session.user_id = 111222333

    pool = MTProtoPoolManager.get_instance()
    pool._clients[account_id] = mock_client

    dispatcher = OutboundDispatcher(pool_manager=pool)

    async with session_factory() as session:
        # Create base account
        acc = Account(
            id=account_id,
            phone="+79998887766",
            title="Lead Manager",
            status=AccountStatus.ACTIVE,
        )
        session.add(acc)
        await session.commit()

        # Execute dispatch
        result = await dispatcher.dispatch(
            session=session,
            account_id=account_id,
            peer_id=peer_id,
            text=outbound_text,
            temp_id=temp_id,
        )

        logger.info(f"Dispatch Result: {result}")
        assert result["temp_id"] == temp_id
        assert result["telegram_message_id"] == 554433
        assert result["status"] == MessageStatus.DELIVERED.value
        assert result["is_outgoing"] is True

        # Verify DB records
        stmt = select(Message).where(Message.telegram_message_id == 554433)
        msg_record = (await session.execute(stmt)).scalar_one()
        assert msg_record.text == outbound_text
        assert msg_record.is_outgoing is True
        assert msg_record.status == MessageStatus.DELIVERED

        # Verify Dialogue updated
        d_stmt = select(Dialogue).where(Dialogue.account_id == account_id, Dialogue.peer_id == peer_id)
        d_record = (await session.execute(d_stmt)).scalar_one()
        assert d_record.last_message_text == outbound_text
        assert d_record.unread_count == 0

    await test_engine.dispose()
    logger.info("Outbound Dispatcher flow PASSED.")
    return True


async def test_websocket_manager_subscriptions() -> bool:
    """Verifies WebSocket manager chat subscriptions and payload broadcasting."""
    logger.info("--- Test 3: WebSocket Connection Manager Subscriptions ---")

    manager = WebSocketConnectionManager.get_instance()
    account_id = uuid.uuid4()
    peer_id = 12345

    # Mock WebSockets
    ws1 = MagicMock()
    ws1.send_json = AsyncMock()
    ws2 = MagicMock()
    ws2.send_json = AsyncMock()

    await manager.subscribe_chat(ws1, account_id, peer_id)
    await manager.subscribe_chat(ws2, account_id, peer_id)

    test_payload = {"type": "new_message", "text": "Live WebSocket broadcast test"}
    await manager.broadcast_to_chat(account_id, peer_id, test_payload)

    ws1.send_json.assert_called_once_with(test_payload)
    ws2.send_json.assert_called_once_with(test_payload)
    logger.info("WebSocket broadcast verified on both mock clients.")

    await manager.disconnect(ws1)
    await manager.disconnect(ws2)
    logger.info("WebSocket cleanup verified.")
    return True


async def main() -> None:
    logger.info("==================================================")
    logger.info("      STARTING SPRINT 3 VERIFICATION SUITE        ")
    logger.info("==================================================")

    assert test_tma_init_data_cryptographic_validator()
    assert await test_outbound_dispatcher_flow()
    assert await test_websocket_manager_subscriptions()

    logger.info("==================================================")
    logger.info("✅ ALL SPRINT 3 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
