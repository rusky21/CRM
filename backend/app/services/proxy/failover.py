import asyncio
import logging
import socket
import time
from datetime import datetime, timezone
from typing import Tuple, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.models.proxy import Proxy
from backend.app.models.account import Account, AccountStatus
from backend.app.services.mtproto.pool_manager import MTProtoPoolManager

logger = logging.getLogger(__name__)


class ProxyFailoverMonitor:
    """
    Monitors health and latency of all proxies in the database.
    Detects dropped proxies and automatically hot-swaps affected accounts
    to healthy backup proxies without requiring manual intervention.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        pool_manager: MTProtoPoolManager,
        check_interval_seconds: int = 60,
    ) -> None:
        self.session_factory = session_factory
        self.pool = pool_manager
        self.interval = check_interval_seconds
        self.is_running: bool = False
        self._task: Optional[asyncio.Task] = None

    async def probe_socket(self, host: str, port: int, timeout_sec: float = 3.0) -> Tuple[bool, int]:
        """
        Attempts a non-blocking TCP socket handshake and measures latency in milliseconds.
        """
        start_time = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout_sec,
            )
            writer.close()
            await writer.wait_closed()
            latency = int((time.time() - start_time) * 1000)
            return True, latency
        except Exception:
            return False, 9999

    async def execute_health_check_cycle(self) -> None:
        """Runs a complete proxy health scan and triggers failovers if needed."""
        async with self.session_factory() as session:
            # 1. Fetch all proxies
            stmt = select(Proxy)
            res = await session.execute(stmt)
            proxies = res.scalars().all()

            failed_proxy_ids = set()
            healthy_proxies = []

            for p in proxies:
                is_alive, latency = await self.probe_socket(p.host, p.port)
                p.last_checked_at = datetime.now(timezone.utc)

                if is_alive:
                    p.is_active = True
                    p.failure_count = 0
                    p.latency_ms = latency
                    healthy_proxies.append(p)
                else:
                    p.failure_count += 1
                    if p.failure_count >= 3:
                        p.is_active = False
                        failed_proxy_ids.add(p.id)
                        logger.warning(
                            f"Proxy {p.host}:{p.port} marked inactive after {p.failure_count} consecutive failures."
                        )

            await session.commit()

            # 2. Check accounts mapped to failed proxies
            if failed_proxy_ids and healthy_proxies:
                backup_proxy = min(healthy_proxies, key=lambda x: x.latency_ms or 9999)

                acc_stmt = select(Account).where(Account.proxy_id.in_(failed_proxy_ids))
                acc_res = await session.execute(acc_stmt)
                affected_accounts = acc_res.scalars().all()

                for acc in affected_accounts:
                    logger.warning(
                        f"Account {acc.id} ({acc.phone}) proxy {acc.proxy_id} failed. Hot-swapping to {backup_proxy.host}:{backup_proxy.port}."
                    )
                    acc.proxy_id = backup_proxy.id
                    acc.proxy = backup_proxy
                    await session.commit()

                    # Re-register client instance with new proxy in MTProto pool
                    try:
                        await self.pool.register_account_instance(acc)
                        await self.pool.get_client(acc.id).connect()
                        logger.info(f"Account {acc.id} reconnected via backup proxy successfully.")
                    except Exception as exc:
                        logger.error(f"Error reconnecting account {acc.id} on backup proxy: {exc}")

    async def start(self) -> None:
        """Starts background watchdog task."""
        if not self._task or self._task.done():
            self.is_running = True
            self._task = asyncio.create_task(self._monitor_loop())
            logger.info("ProxyFailoverMonitor started.")

    async def stop(self) -> None:
        """Stops background watchdog."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ProxyFailoverMonitor stopped.")

    async def _monitor_loop(self) -> None:
        while self.is_running:
            try:
                await self.execute_health_check_cycle()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in ProxyFailoverMonitor cycle: {exc}", exc_info=True)
                await asyncio.sleep(10)
