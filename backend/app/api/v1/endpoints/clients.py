from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.services.crm_bridge import StudioCRMBridge
from backend.app.services.lead_sync import sync_inbound_leads_24h
from backend.app.core.telegram_auth import get_current_tma_user

router = APIRouter(prefix="/clients", tags=["Clients Directory"])


@router.get("", response_model=List[Dict[str, Any]])
async def list_clients(
    filter_24h: bool = Query(False, description="Filter clients active within the last 24 hours"),
    has_orders: bool = Query(False, description="Filter clients who have associated deals/orders"),
    search: Optional[str] = Query(None, description="Search client by name, company, or @username"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> List[Dict[str, Any]]:
    """
    Returns clients fetched directly from the central StudioCRM system (port 5000 / SQLite fallback).
    Includes inlined orders, calculated revenue, active deal status, and Telegram links.
    """
    crm_bridge = StudioCRMBridge.get_instance()
    all_clients = await crm_bridge.get_all_clients()

    results: List[Dict[str, Any]] = []

    for c in all_clients:
        orders = c.get("orders") or []
        total_orders = len(orders)
        total_revenue = sum(float(o.get("totalCost") or 0.0) for o in orders)

        # Find active deal if any
        active_deal = None
        for o in orders:
            st = str(o.get("status") or "")
            if st.lower() in ["new", "inprogress", "pendingpayment", "0", "1"]:
                active_deal = {
                    "id": o.get("id"),
                    "orderNumber": o.get("orderNumber"),
                    "title": o.get("title"),
                    "status": st,
                    "totalCost": float(o.get("totalCost") or 0.0),
                    "deadline": o.get("deadline"),
                }
                break

        # Search filter
        if search:
            q = search.lower().strip()
            name_match = q in (c.get("name") or "").lower()
            person_match = q in (c.get("contactPerson") or "").lower()
            tg_match = q in (c.get("telegram") or "").lower()
            phone_match = q in (c.get("phone") or "")
            if not (name_match or person_match or tg_match or phone_match):
                continue

        # Has orders filter
        if has_orders and total_orders == 0:
            continue

        results.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "contactPerson": c.get("contactPerson"),
            "phone": c.get("phone"),
            "email": c.get("email"),
            "telegram": c.get("telegram"),
            "notes": c.get("notes"),
            "createdAt": c.get("createdAt"),
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "active_deal": active_deal,
            "orders": orders,
        })

    return results[offset : offset + limit]


@router.post("/sync-24h", response_model=Dict[str, Any])
async def trigger_24h_lead_sync(
    db: AsyncSession = Depends(get_db),
    user_auth: Dict[str, Any] = Depends(get_current_tma_user),
) -> Dict[str, Any]:
    """
    Triggers an immediate 24-hour lead synchronization:
    scans all recent Telegram dialogues and ensures they exist as Clients in StudioCRM.
    """
    return await sync_inbound_leads_24h(session=db)
