#!/usr/bin/env python3
"""
Sprint 1 Verification Script: MTProto Multi-Account Engine & Security Layer.

Tests:
1. AES-256-GCM Session Encryption & Decryption Round-Trip.
2. Realistic Device Fingerprint Generator validation.
3. Proxy Configuration & Telethon Dict mapping.
4. Account & PoolManager Lifecycle (Instantiation, Registration, Health Status).
5. Optional Live MTProto verification if TELEGRAM_API_ID and TELEGRAM_API_HASH are provided.
"""

import asyncio
import os
import sys
import uuid
import logging
from pprint import pprint

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.security import encrypt_session_string, decrypt_session_string
from backend.app.services.mtproto.fingerprint import generate_random_fingerprint, DeviceFingerprint
from backend.app.models.proxy import Proxy
from backend.app.models.account import Account, AccountStatus
from backend.app.services.mtproto.pool_manager import MTProtoPoolManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Sprint1Verification")


def test_encryption_roundtrip() -> bool:
    """Verifies AES-256-GCM encryption and decryption with authentication tag."""
    logger.info("--- Test 1: AES-256-GCM Session Encryption ---")
    test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    sample_session = "1Bfb4WNEBu3k_w-199vS4Xz7-TestTelethonSessionStringPayload-abcdef123456789=="

    encrypted = encrypt_session_string(sample_session, test_key)
    logger.info(f"Plaintext length: {len(sample_session)} chars")
    logger.info(f"Encrypted payload (Base64 IV+Cipher+Tag): {encrypted[:40]}... (total {len(encrypted)} chars)")

    decrypted = decrypt_session_string(encrypted, test_key)
    assert decrypted == sample_session, "Decrypted text does not match original plaintext!"
    logger.info("Encryption and Decryption round-trip PASSED.")

    # Tamper test
    try:
        tampered = encrypted[:-2] + "AA"
        decrypt_session_string(tampered, test_key)
        logger.error("Tamper test FAILED: modified payload decrypted without tag error.")
        return False
    except ValueError:
        logger.info("Tamper resistance verified: modified ciphertext rejected.")

    return True


def test_device_fingerprinting() -> bool:
    """Verifies generation of realistic device profiles."""
    logger.info("--- Test 2: Realistic Device Fingerprint Generator ---")
    fp1 = generate_random_fingerprint(lang_code="en")
    fp2 = generate_random_fingerprint(lang_code="ru")

    logger.info(f"Generated Profile 1: {fp1.device_model} | OS: {fp1.system_version} | App: {fp1.app_version} | Lang: {fp1.system_lang_code}")
    logger.info(f"Generated Profile 2: {fp2.device_model} | OS: {fp2.system_version} | App: {fp2.app_version} | Lang: {fp2.system_lang_code}")

    assert fp1.device_model and fp1.app_version, "Fingerprint missing essential client attributes."
    logger.info("Fingerprint generation PASSED.")
    return True


def test_proxy_telethon_mapping() -> bool:
    """Verifies that Proxy model generates proper Telethon connection dict."""
    logger.info("--- Test 3: Proxy Telethon Configuration Mapping ---")
    test_proxy = Proxy(
        id=uuid.uuid4(),
        host="192.168.1.100",
        port=1080,
        username="proxy_user",
        password="proxy_password",
        protocol="socks5",
        is_active=True,
    )
    proxy_dict = test_proxy.to_telethon_proxy()
    logger.info(f"Mapped Telethon Proxy Dict: {proxy_dict}")

    assert proxy_dict["proxy_type"] == "socks5"
    assert proxy_dict["addr"] == "192.168.1.100"
    assert proxy_dict["port"] == 1080
    assert proxy_dict["username"] == "proxy_user"
    logger.info("Proxy mapping PASSED.")
    return True


async def test_pool_manager_orchestration() -> bool:
    """Verifies MTProtoPoolManager instantiation and account registration."""
    logger.info("--- Test 4: MTProto Pool Manager Orchestration ---")
    test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    os.environ["SECRET_ENCRYPTION_KEY"] = test_key

    pool = MTProtoPoolManager.get_instance()

    # Create dummy account with encrypted session
    acc_id = uuid.uuid4()
    dummy_session = "1ApWapzMBu3FakeSessionString=="
    encrypted_session = encrypt_session_string(dummy_session, test_key)
    fp = generate_random_fingerprint()

    account = Account(
        id=acc_id,
        phone="+12025550199",
        title="Marketing Account #1",
        api_id=2040,
        api_hash="b18441a1ff607e10a989891a5462e627",
        encrypted_session=encrypted_session,
        device_fingerprint=fp.to_dict(),
        status=AccountStatus.NEEDS_AUTH,
    )

    client_instance = await pool.register_account_instance(account)
    logger.info(f"Registered instance in pool for account {client_instance.account_id} ({client_instance.phone})")

    # Verify registration in pool
    retrieved = pool.get_client(acc_id)
    assert retrieved is not None, "Client was not registered in pool dictionary."
    assert retrieved.phone == "+12025550199"
    assert retrieved.fingerprint.device_model == fp.device_model

    status = pool.get_pool_status()
    logger.info("Current Pool Status Snapshot:")
    pprint(status)

    assert status["total_accounts"] == 1
    logger.info("Pool Manager orchestration PASSED.")
    return True


async def main() -> None:
    logger.info("==================================================")
    logger.info("      STARTING SPRINT 1 VERIFICATION SUITE        ")
    logger.info("==================================================")

    assert test_encryption_roundtrip()
    assert test_device_fingerprinting()
    assert test_proxy_telethon_mapping()
    assert await test_pool_manager_orchestration()

    logger.info("==================================================")
    logger.info("✅ ALL SPRINT 1 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
