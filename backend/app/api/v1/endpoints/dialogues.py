import os
import shutil
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.models.dialogue import Dialogue
from backend.app.services.mtproto.pool_manager import MTProtoPoolManager
from backend.app.services.outbound_dispatcher import OutboundDispatcher
from backend.app.services.events.producer import MEDIA_CACHE_DIR
from backend.app.core.telegram_auth import get_current_tma_user

router = APIRouter(prefix="/accounts/{account_id}/dialogues", tags=["Dialogues"])


@router.get("", response_model=List[Dict[str, Any]])
async def list_dialogues(
    account_id: UUID,
    search: Optional[str] = Query(None, description="Search by peer name or username"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> List[Dict[str, Any]]:
    """
    Returns a paginated list of dialogues for a specific account, ordered by recent activity.
    """
    stmt = (
        select(Dialogue)
        .where(Dialogue.account_id == account_id)
        .order_by(Dialogue.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if search:
        search_filter = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Dialogue.peer_name.ilike(search_filter),
                Dialogue.peer_username.ilike(search_filter),
                Dialogue.last_message_text.ilike(search_filter),
            )
        )

    result = await db.execute(stmt)
    dialogues = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "account_id": str(d.account_id),
            "peer_id": d.peer_id,
            "peer_name": d.peer_name,
            "peer_username": d.peer_username,
            "unread_count": d.unread_count,
            "last_message_text": d.last_message_text,
            "last_message_at": d.last_message_at.isoformat() if d.last_message_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        }
        for d in dialogues
    ]


@router.post("/{peer_id}/read")
async def mark_dialogue_read(
    account_id: UUID,
    peer_id: int,
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> Dict[str, Any]:
    """
    Marks a dialogue as read: resets unread_count to 0 and notifies Telegram MTProto.
    """
    # 1. Reset unread count in DB
    stmt = (
        update(Dialogue)
        .where(Dialogue.account_id == account_id, Dialogue.peer_id == peer_id)
        .values(unread_count=0)
    )
    res = await db.execute(stmt)
    await db.commit()

    if res.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dialogue not found for given account and peer",
        )

    # 2. Trigger MTProto read acknowledge on Telegram servers
    pool = MTProtoPoolManager.get_instance()
    client_instance = pool.get_client(account_id)
    if client_instance and client_instance.is_connected:
        try:
            await client_instance.client.send_read_acknowledge(peer_id)
        except Exception as exc:
            pass  # Suppress non-critical acknowledge failure

    return {
        "account_id": str(account_id),
        "peer_id": peer_id,
        "unread_count": 0,
        "status": "marked_as_read",
    }


@router.post("/{peer_id}/media")
async def upload_media_message(
    account_id: UUID,
    peer_id: int,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> Dict[str, Any]:
    """
    Uploads a photo or document file and dispatches it through Telethon MTProto to the peer.
    """
    pool = MTProtoPoolManager.get_instance()
    dispatcher = OutboundDispatcher(pool_manager=pool)

    # Determine file classification
    filename = file.filename or "attachment.bin"
    ext = os.path.splitext(filename)[1].lower()
    media_type = "photo" if ext in [".jpg", ".jpeg", ".png", ".webp"] else "document"

    safe_name = f"upload_{UUID.int.__hash__(account_id)}_{int(os.times().elapsed)}_{filename}"
    temp_path = os.path.join(MEDIA_CACHE_DIR, safe_name)

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = await dispatcher.send_media(
            session=db,
            account_id=account_id,
            peer_id=peer_id,
            file_path=temp_path,
            caption=caption,
            media_type=media_type,
            media_url=f"/media/{safe_name}",
        )
        return result
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ACCOUNT_BANNED_READ_ONLY: Cannot send media from a banned account.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch media: {exc}",
        )
