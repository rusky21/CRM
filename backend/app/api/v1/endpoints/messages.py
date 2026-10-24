from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.models.message import Message
from backend.app.core.telegram_auth import get_current_tma_user

router = APIRouter(prefix="/accounts/{account_id}/dialogues/{peer_id}/messages", tags=["Messages"])


@router.get("", response_model=List[Dict[str, Any]])
async def get_chat_history(
    account_id: UUID,
    peer_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    before_msg_id: Optional[int] = Query(None, description="Fetch messages prior to this telegram_message_id"),
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> List[Dict[str, Any]]:
    """
    Fetches historical messages for a chat dialogue ordered chronologically.
    Supports cursor pagination via 'before_msg_id' for infinite scroll.
    """
    stmt = (
        select(Message)
        .where(Message.account_id == account_id, Message.peer_id == peer_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if before_msg_id:
        stmt = stmt.where(Message.telegram_message_id < before_msg_id)

    result = await db.execute(stmt)
    messages = result.scalars().all()

    # Return ordered chronologically for frontend chat view
    return [
        {
            "id": str(m.id),
            "dialogue_id": str(m.dialogue_id) if m.dialogue_id else None,
            "account_id": str(m.account_id),
            "peer_id": m.peer_id,
            "telegram_message_id": m.telegram_message_id,
            "sender_id": m.sender_id,
            "is_outgoing": m.is_outgoing,
            "text": m.text,
            "media_type": m.media_type,
            "status": m.status.value,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in reversed(messages)
    ]
