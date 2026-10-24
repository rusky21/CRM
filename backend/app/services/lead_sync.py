import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.dialogue import Dialogue
from backend.app.models.account import Account
from backend.app.services.crm_bridge import StudioCRMBridge

logger = logging.getLogger(__name__)


async def sync_inbound_leads_24h(session: AsyncSession) -> Dict[str, Any]:
    """
    Scans all Telegram dialogues active within the last 24 hours
    and synchronizes fresh leads directly into the existing StudioCRM database/API.
    """
    crm_bridge = StudioCRMBridge.get_instance()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    stmt = (
        select(Dialogue, Account)
        .join(Account, Dialogue.account_id == Account.id)
        .where(Dialogue.last_message_at >= cutoff)
    )
    result = await session.execute(stmt)
    rows = result.all()

    synced_count = 0
    errors_count = 0
    synced_clients: List[Dict[str, Any]] = []

    for d, acc in rows:
        try:
            account_title = acc.custom_title or acc.title
            notes = f"Telegram Lead via [{account_title}] ({acc.phone})"
            if d.last_message_text:
                notes += f" | Last msg: «{d.last_message_text[:80]}»"

            client_record = await crm_bridge.create_or_update_client(
                name=d.peer_name,
                telegram=d.peer_username,
                notes=notes,
            )
            synced_count += 1
            synced_clients.append({
                "peer_id": d.peer_id,
                "peer_name": d.peer_name,
                "crm_client_id": client_record.get("id"),
                "telegram": client_record.get("telegram"),
            })
        except Exception as exc:
            logger.error(f"Error syncing lead {d.peer_name} ({d.peer_id}) to StudioCRM: {exc}")
            errors_count += 1

    return {
        "status": "success",
        "scanned_24h_dialogues": len(rows),
        "synced_leads": synced_count,
        "errors": errors_count,
        "synced_clients": synced_clients,
    }


async def auto_sync_single_lead(
    peer_name: str,
    peer_username: str = None,
    peer_phone: str = None,
    account_title: str = None,
    initial_text: str = None,
) -> Dict[str, Any]:
    """
    Instantly ensures an inbound Telegram sender is registered as a Lead in StudioCRM.
    """
    crm_bridge = StudioCRMBridge.get_instance()
    notes = f"Auto-created Telegram lead"
    if account_title:
        notes += f" from account [{account_title}]"
    if initial_text:
        notes += f" | Inbound message: «{initial_text[:80]}»"

    return await crm_bridge.create_or_update_client(
        name=peer_name,
        telegram=peer_username,
        phone=peer_phone,
        notes=notes,
    )
