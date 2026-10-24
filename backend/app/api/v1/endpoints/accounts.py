import os
import shutil
import tempfile
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon.sessions import StringSession

from backend.app.core.config import settings
from backend.app.core.security import encrypt_session_string
from backend.app.db.session import get_db
from backend.app.models.account import Account, AccountStatus
from backend.app.models.proxy import Proxy
from backend.app.models.dialogue import Dialogue
from backend.app.services.mtproto.pool_manager import MTProtoPoolManager
from backend.app.services.mtproto.fingerprint import generate_random_fingerprint
from backend.app.core.telegram_auth import get_current_tma_user

router = APIRouter(prefix="/accounts", tags=["Accounts"])


class AliasUpdateRequest(BaseModel):
    custom_title: str = Field(..., min_length=1, max_length=100)


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, max_length=128)
    last_name: Optional[str] = Field(None, max_length=128)
    about: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, max_length=64)


@router.get("", response_model=List[Dict[str, Any]])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> List[Dict[str, Any]]:
    """
    Returns all managed Telegram accounts with their live MTProto connection status
    and aggregated unread dialogues counter.
    """
    pool = MTProtoPoolManager.get_instance()

    # Query accounts
    stmt = select(Account).order_by(Account.created_at.desc())
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    # Calculate unread counts per account
    unread_stmt = (
        select(Dialogue.account_id, func.sum(Dialogue.unread_count).label("total_unread"))
        .where(Dialogue.unread_count > 0)
        .group_by(Dialogue.account_id)
    )
    unread_res = await db.execute(unread_stmt)
    unread_map = {row.account_id: int(row.total_unread) for row in unread_res}

    response = []
    for acc in accounts:
        # Check live status in pool
        client = pool.get_client(acc.id)
        live_status = client.status.value if client else acc.status.value
        is_connected = client.is_connected if client else False

        response.append({
            "id": str(acc.id),
            "phone": acc.phone,
            "title": acc.title,
            "custom_title": acc.custom_title,
            "username": acc.username,
            "first_name": acc.first_name,
            "last_name": acc.last_name,
            "about": acc.about,
            "status": live_status,
            "is_connected": is_connected,
            "total_unread_dialogues": unread_map.get(acc.id, 0),
            "proxy": {
                "id": str(acc.proxy.id),
                "host": acc.proxy.host,
                "port": acc.proxy.port,
                "protocol": acc.proxy.protocol,
                "latency_ms": acc.proxy.latency_ms,
            } if acc.proxy else None,
            "device_model": acc.device_fingerprint.get("device_model") if acc.device_fingerprint else None,
            "created_at": acc.created_at.isoformat() if acc.created_at else None,
        })

    return response


@router.post("/{account_id}/reconnect")
async def reconnect_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> Dict[str, Any]:
    """Forces reconnection of an account's Telethon client in the pool."""
    pool = MTProtoPoolManager.get_instance()
    client = pool.get_client(account_id)

    if not client:
        # Try registering instance from database
        stmt = select(Account).where(Account.id == account_id)
        res = await db.execute(stmt)
        account = res.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

        client = await pool.register_account_instance(account)

    success = await client.connect()
    return {
        "account_id": str(account_id),
        "status": client.status.value,
        "is_connected": client.is_connected,
        "success": success,
    }


@router.post("/import-file")
async def import_session_file(
    file: UploadFile = File(...),
    custom_title: Optional[str] = Form(None),
    proxy_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> Dict[str, Any]:
    """
    Imports an account directly via a Telethon .session binary file or .txt StringSession file.
    Validates MTProto handshake, inspects get_me(), encrypts session, and registers in pool.
    """
    pool = MTProtoPoolManager.get_instance()
    file_bytes = await file.read()
    filename = file.filename or "session.bin"

    # Resolve proxy if specified
    proxy_config = None
    proxy_uuid = None
    if proxy_id:
        try:
            proxy_uuid = UUID(proxy_id)
            proxy_stmt = select(Proxy).where(Proxy.id == proxy_uuid)
            proxy_res = await db.execute(proxy_stmt)
            proxy_obj = proxy_res.scalar_one_or_none()
            if proxy_obj:
                proxy_config = proxy_obj.to_telethon_proxy()
        except ValueError:
            pass

    api_id = settings.DEFAULT_TELEGRAM_API_ID
    api_hash = settings.DEFAULT_TELEGRAM_API_HASH
    extracted_string_session: Optional[str] = None
    telegram_user = None

    # Detect file format: text string session vs sqlite binary session
    is_text = False
    try:
        decoded_text = file_bytes.decode("utf-8").strip()
        if len(decoded_text) > 50 and "\x00" not in decoded_text:
            is_text = True
    except UnicodeDecodeError:
        is_text = False

    if is_text:
        # StringSession parsing
        session_instance = StringSession(decoded_text)
        temp_client = TelegramClient(session_instance, api_id, api_hash, proxy=proxy_config)
        try:
            await temp_client.connect()
            if not await temp_client.is_user_authorized():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="StringSession is invalid, revoked, or requires re-authentication.",
                )
            telegram_user = await temp_client.get_me()
            extracted_string_session = decoded_text
        finally:
            await temp_client.disconnect()
    else:
        # Binary Telethon SQLite .session file
        temp_dir = tempfile.mkdtemp(prefix="tg_session_")
        session_base_name = f"import_{uuid4().hex}"
        session_file_path = os.path.join(temp_dir, f"{session_base_name}.session")
        try:
            with open(session_file_path, "wb") as f:
                f.write(file_bytes)

            temp_client = TelegramClient(
                os.path.join(temp_dir, session_base_name), api_id, api_hash, proxy=proxy_config
            )
            await temp_client.connect()
            if not await temp_client.is_user_authorized():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Binary .session file is unauthorized or expired.",
                )
            telegram_user = await temp_client.get_me()
            extracted_string_session = StringSession.save(temp_client.session)
            await temp_client.disconnect()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    if not telegram_user or not extracted_string_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to authenticate session against Telegram MTProto cloud.",
        )

    phone = getattr(telegram_user, "phone", None)
    if not phone:
        phone = f"+{telegram_user.id}"

    # Check for existing account
    existing_stmt = select(Account).where(Account.phone == phone)
    existing_res = await db.execute(existing_stmt)
    existing_account = existing_res.scalar_one_or_none()

    encrypted_session = encrypt_session_string(
        extracted_string_session, settings.SECRET_ENCRYPTION_KEY
    )
    title = custom_title or f"{telegram_user.first_name or ''} {telegram_user.last_name or ''}".strip() or phone

    if existing_account:
        # Update existing record
        existing_account.title = title
        existing_account.custom_title = custom_title
        existing_account.first_name = telegram_user.first_name
        existing_account.last_name = telegram_user.last_name
        existing_account.username = telegram_user.username
        existing_account.telegram_user_id = telegram_user.id
        existing_account.encrypted_session = encrypted_session
        existing_account.status = AccountStatus.ACTIVE
        if proxy_uuid:
            existing_account.proxy_id = proxy_uuid
        account_record = existing_account
    else:
        # Create new account
        account_record = Account(
            id=uuid4(),
            phone=phone,
            title=title,
            custom_title=custom_title,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            username=telegram_user.username,
            telegram_user_id=telegram_user.id,
            encrypted_session=encrypted_session,
            status=AccountStatus.ACTIVE,
            proxy_id=proxy_uuid,
            device_fingerprint=generate_random_fingerprint().to_dict(),
        )
        db.add(account_record)

    await db.commit()
    await db.refresh(account_record)

    # Register in active MTProto pool and start listener
    client_inst = await pool.register_account_instance(
        account_record, raw_session_string=extracted_string_session
    )
    await client_inst.connect()

    return {
        "id": str(account_record.id),
        "phone": account_record.phone,
        "title": account_record.title,
        "custom_title": account_record.custom_title,
        "username": account_record.username,
        "first_name": account_record.first_name,
        "last_name": account_record.last_name,
        "status": client_inst.status.value,
        "is_connected": client_inst.is_connected,
        "message": "Session imported and activated successfully.",
    }


@router.patch("/{account_id}/alias")
async def update_account_alias(
    account_id: UUID,
    payload: AliasUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> Dict[str, Any]:
    """Updates the internal operator alias (custom_title) for an account."""
    stmt = (
        update(Account)
        .where(Account.id == account_id)
        .values(custom_title=payload.custom_title.strip())
        .returning(Account)
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()
    await db.commit()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    return {
        "id": str(account.id),
        "title": account.title,
        "custom_title": account.custom_title,
        "phone": account.phone,
    }


@router.put("/{account_id}/profile")
async def update_telegram_profile(
    account_id: UUID,
    payload: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> Dict[str, Any]:
    """
    Updates Account Profile on Telegram MTProto Cloud (Name, Bio, Username)
    and syncs changes to the local database.
    """
    pool = MTProtoPoolManager.get_instance()
    client = pool.get_client(account_id)
    if not client or not client.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MTProto client is offline or not connected to Telegram cloud.",
        )

    # 1. Update Profile (First Name, Last Name, About)
    if payload.first_name is not None or payload.last_name is not None or payload.about is not None:
        await client.update_profile(
            first_name=payload.first_name,
            last_name=payload.last_name,
            about=payload.about,
        )

    # 2. Update Username if specified
    if payload.username is not None:
        await client.update_username(payload.username)

    # 3. Sync with local database
    update_vals: Dict[str, Any] = {}
    if payload.first_name is not None:
        update_vals["first_name"] = payload.first_name
    if payload.last_name is not None:
        update_vals["last_name"] = payload.last_name
    if payload.about is not None:
        update_vals["about"] = payload.about
    if payload.username is not None:
        update_vals["username"] = payload.username.lstrip("@").strip()

    if update_vals:
        await db.execute(
            update(Account).where(Account.id == account_id).values(**update_vals)
        )
        await db.commit()

    return {
        "account_id": str(account_id),
        "status": "profile_updated",
        "updated_fields": list(update_vals.keys()),
    }


@router.post("/{account_id}/profile/avatar")
async def upload_account_avatar(
    account_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> Dict[str, Any]:
    """Uploads and changes profile photo on Telegram cloud for this account."""
    pool = MTProtoPoolManager.get_instance()
    client = pool.get_client(account_id)
    if not client or not client.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MTProto client is offline.",
        )

    file_bytes = await file.read()
    temp_dir = tempfile.mkdtemp(prefix="tg_avatar_")
    safe_file_path = os.path.join(temp_dir, file.filename or "avatar.jpg")
    try:
        with open(safe_file_path, "wb") as f:
            f.write(file_bytes)
        await client.upload_profile_photo(safe_file_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return {
        "account_id": str(account_id),
        "status": "avatar_updated",
        "filename": file.filename,
    }


@router.post("/{account_id}/terminate-sessions")
async def terminate_account_sessions(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> Dict[str, Any]:
    """Wipes all other active Telegram sessions except this CRM connection."""
    pool = MTProtoPoolManager.get_instance()
    client = pool.get_client(account_id)
    if not client or not client.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MTProto client is offline.",
        )

    res = await client.terminate_other_sessions()
    return {
        "account_id": str(account_id),
        "status": "other_sessions_terminated",
        "success": res,
    }
