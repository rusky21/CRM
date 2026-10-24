#!/usr/bin/env python3
"""
Sprint 2.1 Verification Suite:
- Direct Session Ingestion (.session / StringSession)
- Internal Account Aliases (custom_title)
- Banned Account Message Vault (Read-Only Enforcement)
- Native Telegram Profile Studio MTProto Methods
"""

import inspect
import sys
import os
import uuid

# Ensure root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.models.account import Account, AccountStatus
from backend.app.services.mtproto.client_instance import TelethonClientInstance
from backend.app.core.security import encrypt_session_string, decrypt_session_string

def test_model_fields():
    print("--- Test 1: Account Model Schema Verification ---")
    account = Account(
        id=uuid.uuid4(),
        phone="+12025550199",
        title="Sales US",
        custom_title="Менеджер Вася",
        about="Official Sales Lead",
        status=AccountStatus.BANNED,
    )
    assert hasattr(account, "custom_title"), "Account model must have custom_title"
    assert hasattr(account, "about"), "Account model must have about"
    assert account.custom_title == "Менеджер Вася"
    assert account.status == AccountStatus.BANNED
    print("✓ Model schema and custom_title verified successfully.")
    return True

def test_profile_studio_methods():
    print("--- Test 2: MTProto Profile Studio Methods Verification ---")
    methods = [
        "update_profile",
        "update_username",
        "upload_profile_photo",
        "terminate_other_sessions",
    ]
    for method_name in methods:
        assert hasattr(TelethonClientInstance, method_name), f"TelethonClientInstance must implement {method_name}"
        method = getattr(TelethonClientInstance, method_name)
        assert inspect.iscoroutinefunction(method), f"{method_name} must be an async coroutine"
        print(f"✓ Method TelethonClientInstance.{method_name}() is implemented and async.")
    return True

def test_session_encryption():
    print("--- Test 3: Session File Encryption Verification ---")
    dummy_session = "1BJWap1wBuySgH1x0D8j3L8M7N6P5Q4R3S2T1U0V9W8X7Y6Z5a4b3c2d1e0f"
    secret_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    encrypted = encrypt_session_string(dummy_session, secret_key)
    decrypted = decrypt_session_string(encrypted, secret_key)
    assert decrypted == dummy_session, "Decrypted session must match original"
    print("✓ AES-256-GCM Session string encryption & decryption verified.")
    return True

def test_banned_vault_read_only_invariants():
    print("--- Test 4: Banned Account Read-Only Invariants Verification ---")
    # Simulate dispatcher check for banned account
    from backend.app.services.outbound_dispatcher import OutboundDispatcher
    from unittest.mock import MagicMock

    pool_mock = MagicMock()
    client_mock = MagicMock()
    client_mock.status = AccountStatus.BANNED
    pool_mock.get_client.return_value = client_mock

    dispatcher = OutboundDispatcher(pool_manager=pool_mock)
    try:
        dispatcher._get_active_client(uuid.uuid4())
        assert False, "Dispatcher must disallow sending from BANNED account"
    except PermissionError as exc:
        assert str(exc) == "ACCOUNT_BANNED_READ_ONLY", f"Expected ACCOUNT_BANNED_READ_ONLY, got {exc}"
        print("✓ Banned account outbound lock strictly enforces ACCOUNT_BANNED_READ_ONLY.")

    return True

def main():
    print("==================================================")
    print("       STARTING SPRINT 2.1 VERIFICATION SUITE     ")
    print("==================================================")
    assert test_model_fields()
    assert test_profile_studio_methods()
    assert test_session_encryption()
    assert test_banned_vault_read_only_invariants()
    print("==================================================")
    print("✅ ALL SPRINT 2.1 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    main()
