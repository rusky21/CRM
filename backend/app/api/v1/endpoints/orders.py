from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.services.crm_bridge import StudioCRMBridge
from backend.app.core.telegram_auth import get_current_tma_user

router = APIRouter(prefix="/orders", tags=["Orders"])


class InChatOrderCreateRequest(BaseModel):
    account_id: Optional[UUID] = None
    peer_id: int
    peer_name: str = Field(..., min_length=1)
    peer_username: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    total_cost: float = Field(..., ge=0)
    deadline: Optional[str] = None
    notes: Optional[str] = None
    status: str = Field(default="New")


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_in_chat_order(
    payload: InChatOrderCreateRequest,
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> Dict[str, Any]:
    """
    Creates an official Order directly in the central StudioCRM system:
    1. Resolves or automatically creates the Client in StudioCRM based on Telegram metadata.
    2. Calls StudioCRM POST /api/orders to create the order and generate the official orderNumber.
    """
    crm_bridge = StudioCRMBridge.get_instance()

    # 1. Resolve or register client in StudioCRM
    client = await crm_bridge.find_client_by_telegram(username=payload.peer_username)
    if not client:
        client = await crm_bridge.create_or_update_client(
            name=payload.peer_name,
            telegram=payload.peer_username,
            notes=f"Created via in-chat order action for Telegram peer ID {payload.peer_id}",
        )

    client_id = client.get("id")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve or create Client record in StudioCRM.",
        )

    # 2. Create Order in StudioCRM
    order = await crm_bridge.create_order(
        client_id=client_id,
        title=payload.title,
        total_cost=payload.total_cost,
        deadline=payload.deadline,
        notes=payload.notes,
        status=payload.status,
    )

    return {
        "status": "order_created",
        "client_id": client_id,
        "client_name": client.get("name"),
        "telegram": client.get("telegram"),
        "order": order,
    }


@router.get("/by-peer/{peer_id}", response_model=List[Dict[str, Any]])
async def get_orders_by_telegram_peer(
    peer_id: int,
    username: Optional[str] = Query(None, description="Telegram @username of the peer"),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> List[Dict[str, Any]]:
    """
    Fetches all orders from StudioCRM associated with this Telegram peer.
    """
    crm_bridge = StudioCRMBridge.get_instance()
    client = await crm_bridge.find_client_by_telegram(username=username)
    if not client or not client.get("id"):
        return []

    return await crm_bridge.get_orders_for_client(client["id"])
