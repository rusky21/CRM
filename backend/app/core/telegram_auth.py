import hmac
import hashlib
import json
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status, Query

from backend.app.core.config import settings


def parse_and_validate_telegram_init_data(
    init_data_raw: str,
    bot_token: str,
    max_age_seconds: int = 86400,  # 24 hours
) -> Dict[str, Any]:
    """
    Validates Telegram Mini App initData according to the official Telegram protocol.
    
    1. Parses query string into dictionary.
    2. Extracts the 'hash' field.
    3. Sorts remaining key-value pairs alphabetically.
    4. Constructs data_check_string: "key=value\\n...".
    5. Computes secret_key = HMAC_SHA256("WebAppData", bot_token).
    6. Computes calculated_hash = HMAC_SHA256(secret_key, data_check_string).hex().
    7. Verifies calculated_hash matches 'hash' using constant-time comparison.
    8. Validates auth_date freshness.
    """
    if not init_data_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram initData is missing",
        )

    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data_raw, keep_blank_values=True))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed initData query string: {exc}",
        ) from exc

    received_hash = parsed_data.pop("hash", None)
    if not received_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing 'hash' parameter in initData",
        )

    # Sort key-value pairs alphabetically and form data_check_string
    sorted_pairs = sorted(parsed_data.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_pairs)

    # Compute secret key: HMAC_SHA256(key="WebAppData", msg=bot_token)
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    # Compute hash of data_check_string
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Constant time comparison to prevent timing attacks
    if not hmac.compare_digest(calculated_hash.lower(), received_hash.lower()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initData signature",
        )

    # Validate auth_date if present
    auth_date_raw = parsed_data.get("auth_date")
    if auth_date_raw:
        try:
            auth_timestamp = int(auth_date_raw)
            current_timestamp = int(datetime.now(timezone.utc).timestamp())
            if current_timestamp - auth_timestamp > max_age_seconds:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Telegram initData has expired",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid auth_date integer format",
            )

    # Parse user JSON payload if available
    user_raw = parsed_data.get("user")
    if user_raw:
        try:
            parsed_data["user"] = json.loads(user_raw)
        except Exception:
            pass

    return parsed_data


async def get_current_tma_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    init_data_query: Optional[str] = Query(None, alias="initData"),
) -> Dict[str, Any]:
    """
    FastAPI dependency for authenticating requests originating from Telegram Mini App.
    Accepts initData via 'X-Telegram-Init-Data' header or 'initData' query parameter.
    """
    init_data = x_telegram_init_data or init_data_query

    # Bypass in local debug mode only if explicitly allowed and no initData is passed
    if not init_data and settings.DEBUG:
        return {
            "debug_mode": True,
            "user": {
                "id": settings.ADMIN_CHAT_ID or 12345678,
                "first_name": "Dev",
                "username": "developer",
            },
        }

    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Telegram-Init-Data header or initData query parameter required",
        )

    if not settings.ADMIN_BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_BOT_TOKEN not configured on server",
        )

    return parse_and_validate_telegram_init_data(
        init_data_raw=init_data,
        bot_token=settings.ADMIN_BOT_TOKEN,
    )
