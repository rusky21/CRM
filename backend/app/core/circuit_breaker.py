import asyncio
import logging
import time
from typing import Dict, Tuple, Optional
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.errors import FloodWaitError, PeerFloodError

from backend.app.models.account import Account, AccountStatus

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Guards Telegram accounts against MTProto rate-limiting and bans.
    Tracks FloodWait cooldowns, throttles peer-level outbound bursts,
    and coordinates account status state changes in PostgreSQL.
    """

    _instance: Optional["CircuitBreaker"] = None

    def __init__(self) -> None:
        # account_id -> cooldown_end_timestamp
        self._flood_wait_expirations: Dict[UUID, float] = {}
        # (account_id, peer_id) -> last_outbound_timestamp
        self._peer_last_outbound: Dict[Tuple[UUID, int], float] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "CircuitBreaker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def check_account_available(self, account_id: UUID) -> Tuple[bool, int]:
        """
        Verifies if an account is currently free from FloodWait constraints.
        Returns: (is_available, remaining_cooldown_seconds)
        """
        async with self._lock:
            expiration = self._flood_wait_expirations.get(account_id)
            if not expiration:
                return True, 0

            now = time.time()
            if now >= expiration:
                # Cooldown expired, clear restriction
                del self._flood_wait_expirations[account_id]
                logger.info(f"FloodWait cooldown expired for account {account_id}. Account unlocked.")
                return True, 0

            remaining = int(expiration - now)
            return False, remaining

    async def record_flood_wait(
        self,
        account_id: UUID,
        wait_seconds: int,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """
        Enforces a FloodWait cooldown on an account and updates DB status to FLOOD_WAIT.
        """
        # Buffer with an extra 2 seconds for safety
        expiration = time.time() + wait_seconds + 2
        async with self._lock:
            self._flood_wait_expirations[account_id] = expiration

        logger.warning(
            f"Account {account_id} placed under FloodWait for {wait_seconds}s (expires at {int(expiration)})."
        )

        if session:
            try:
                stmt = (
                    update(Account)
                    .where(Account.id == account_id)
                    .values(status=AccountStatus.FLOOD_WAIT)
                )
                await session.execute(stmt)
                await session.commit()
            except Exception as exc:
                logger.error(f"Failed updating Account {account_id} status to FLOOD_WAIT: {exc}")

    async def record_peer_flood(
        self,
        account_id: UUID,
        peer_id: int,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """
        Handles PeerFloodError (Telegram flags account as sending too many messages to a specific user).
        Imposes a minimum 300-second pause on outbound messages to this specific peer.
        """
        logger.error(f"PeerFloodError detected on Account {account_id} with Peer {peer_id}.")
        async with self._lock:
            self._peer_last_outbound[(account_id, peer_id)] = time.time() + 300

    async def enforce_rate_limit(
        self,
        account_id: UUID,
        peer_id: int,
        min_interval_seconds: float = 1.0,
    ) -> None:
        """
        Applies a minimum interval between sequential messages to the same peer
        to prevent bot-like burst behavior.
        """
        key = (account_id, peer_id)
        now = time.time()
        async with self._lock:
            last_sent = self._peer_last_outbound.get(key, 0)
            elapsed = now - last_sent
            if elapsed < min_interval_seconds:
                sleep_needed = min_interval_seconds - elapsed
                await asyncio.sleep(sleep_needed)
            self._peer_last_outbound[key] = time.time()
