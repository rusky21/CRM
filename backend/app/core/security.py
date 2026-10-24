import base64
import binascii
import os
from typing import Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


def _normalize_key(key: Union[str, bytes]) -> bytes:
    """Ensure the key is a raw 32-byte binary object."""
    if isinstance(key, str):
        key = key.strip()
        try:
            raw_key = binascii.unhexlify(key)
        except binascii.Error:
            raw_key = key.encode("utf-8")
    else:
        raw_key = key

    if len(raw_key) != 32:
        raise ValueError(f"AES-256 requires a 32-byte key, provided key is {len(raw_key)} bytes.")
    return raw_key


def encrypt_session_string(plain_text: str, secret_key: Union[str, bytes]) -> str:
    """
    Encrypts a session string using AES-256-GCM.
    
    Structure of output (Base64 encoded):
    [12 bytes IV / Nonce] + [Ciphertext + 16 bytes Authentication Tag]
    """
    if not plain_text:
        raise ValueError("Cannot encrypt an empty session string.")

    key = _normalize_key(secret_key)
    aesgcm = AESGCM(key)

    # 96-bit (12-byte) nonce standard for AES-GCM
    nonce = os.urandom(12)
    plain_bytes = plain_text.encode("utf-8")

    # AESGCM automatically computes and appends the 16-byte tag to the ciphertext
    encrypted_data = aesgcm.encrypt(nonce, plain_bytes, None)

    # Combine nonce + ciphertext_with_tag
    payload = nonce + encrypted_data
    return base64.b64encode(payload).decode("utf-8")


def decrypt_session_string(encrypted_blob: str, secret_key: Union[str, bytes]) -> str:
    """
    Decrypts an AES-256-GCM base64-encoded encrypted session blob.
    
    Validates authenticity via the GCM tag. Raises ValueError on corruption or tampering.
    """
    if not encrypted_blob:
        raise ValueError("Cannot decrypt an empty session blob.")

    key = _normalize_key(secret_key)
    aesgcm = AESGCM(key)

    try:
        raw_payload = base64.b64decode(encrypted_blob)
    except Exception as exc:
        raise ValueError("Invalid Base64 format in encrypted blob.") from exc

    if len(raw_payload) < 28:  # 12 bytes IV + 16 bytes Tag minimum
        raise ValueError("Encrypted blob is too short to contain a valid IV and Tag.")

    nonce = raw_payload[:12]
    ciphertext_with_tag = raw_payload[12:]

    try:
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return decrypted_bytes.decode("utf-8")
    except InvalidTag as exc:
        raise ValueError("Authentication tag mismatch: data is corrupted or key is incorrect.") from exc
    except UnicodeDecodeError as exc:
        raise ValueError("Decrypted plaintext is not valid UTF-8.") from exc
