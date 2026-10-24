import asyncio
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import events

from backend.app.core.config import settings
from backend.app.core.security import decrypt_session_string
from backend.app.models.account import Account, AccountStatus
from backend.app.services.mtproto.client_instance import TelethonClientInstance, MessageHandlerCallback
from backend.app.services.mtproto.fingerprint import DeviceFingerprint, generate_random_fingerprint

logger = logging.getLogger(__name__)


class MTProtoPoolManager:
    """
    Central orchestrator managing concurrent Telethon client instances.
    Provides session decryption, proxy attachment, parallel startup,
    health monitoring, and global event listener fanout.
    """

    _instance: Optional["MTProtoPoolManager"] = None

    def __init__(self) -> None:
        self._clients: Dict[UUID, TelethonClientInstance] = {}
        self._lock = asyncio.Lock()
        self._global_handlers: List[MessageHandlerCallback] = []
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_running: bool = False

    @classmethod
    def get_instance(cls) -> "MTProtoPoolManager":
        """Singleton accessor."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_global_message_handler(self, handler: MessageHandlerCallback) -> None:
        """Registers a global callback invoked whenever ANY account in the pool receives a message."""
        self._global_handlers.append(handler)
        for client in self._clients.values():
            client.set_message_handler(self._dispatch_global_event)

    async def _dispatch_global_event(self, account_id: UUID, event: events.NewMessage.Event) -> None:
        """Dispatches an incoming update event to all registered global handlers."""
        for handler in self._global_handlers:
            try:
                await handler(account_id, event)
            except Exception as exc:
                logger.error(f"Global handler error for account {account_id}: {exc}", exc_info=True)

    def get_client(self, account_id: UUID) -> Optional[TelethonClientInstance]:
        """Retrieves a client instance by its account ID."""
        return self._clients.get(account_id)

    async def register_account_instance(
        self,
        account: Account,
        raw_session_string: Optional[str] = None,
    ) -> TelethonClientInstance:
        """
        Builds and registers a TelethonClientInstance from an Account model.
        Decrypts stored session if available.
        """
        async with self._lock:
            # If instance already exists, disconnect first
            if account.id in self._clients:
                await self._clients[account.id].disconnect()

            # Session decryption
            decrypted_session = raw_session_string
            if not decrypted_session and account.encrypted_session:
                try:
                    decrypted_session = decrypt_session_string(
                        account.encrypted_session, settings.SECRET_ENCRYPTION_KEY
                    )
                except Exception as exc:
                    logger.error(f"Failed to decrypt session for account {account.id}: {exc}")

            # Fingerprint resolution
            if account.device_fingerprint and isinstance(account.device_fingerprint, dict):
                fingerprint = DeviceFingerprint.from_dict(account.device_fingerprint)
            else:
                fingerprint = generate_random_fingerprint()

            # API credentials resolution
            api_id = account.api_id or settings.DEFAULT_TELEGRAM_API_ID
            api_hash = account.api_hash or settings.DEFAULT_TELEGRAM_API_HASH
            if not api_id or not api_hash:
                raise ValueError(
                    f"Account {account.id} ({account.phone}) lacks api_id/api_hash and no system default is set."
                )

            # Proxy configuration
            proxy_config = account.proxy.to_telethon_proxy() if account.proxy else None

            client_instance = TelethonClientInstance(
                account_id=account.id,
                phone=account.phone,
                api_id=api_id,
                api_hash=api_hash,
                fingerprint=fingerprint,
                session_string=decrypted_session,
                proxy_config=proxy_config,
            )

            client_instance.set_message_handler(self._dispatch_global_event)
            self._clients[account.id] = client_instance
            return client_instance

    async def initialize_from_db(self, db_session: AsyncSession) -> Dict[str, int]:
        """
        Loads all ACTIVE accounts with proxies from the database and boots them concurrently.
        """
        stmt = (
            select(Account)
            .where(Account.status.in_([AccountStatus.ACTIVE, AccountStatus.CONNECTING]))
        )
        result = await db_session.execute(stmt)
        accounts = result.scalars().all()

        logger.info(f"Discovered {len(accounts)} candidate accounts in database for pool startup.")

        # Instantiate clients
        for account in accounts:
            try:
                await self.register_account_instance(account)
            except Exception as exc:
                logger.error(f"Failed initializing instance for account {account.id}: {exc}")

        # Connect concurrently
        connect_tasks = [client.connect() for client in self._clients.values()]
        results = await asyncio.gather(*connect_tasks, return_exceptions=True)

        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful

        self._start_health_monitor()
        logger.info(f"Pool startup complete. Connected: {successful}, Failed: {failed}")
        return {"total": len(self._clients), "connected": successful, "failed": failed}

    async def stop_client(self, account_id: UUID) -> None:
        """Gracefully stops and removes an individual account from the pool."""
        async with self._lock:
            client = self._clients.pop(account_id, None)
            if client:
                await client.disconnect()

    async def stop_all(self) -> None:
        """Gracefully disconnects all active Telethon instances and stops monitor."""
        self._is_running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()

        disconnect_tasks = [client.disconnect() for client in self._clients.values()]
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        self._clients.clear()
        logger.info("All MTProto pool instances stopped.")

    def get_pool_status(self) -> Dict[str, Any]:
        """Returns runtime diagnostics of all pooled accounts."""
        status_counts: Dict[str, int] = {}
        client_details = []

        for acc_id, client in self._clients.items():
            st = client.status.value
            status_counts[st] = status_counts.get(st, 0) + 1
            client_details.append({
                "account_id": str(acc_id),
                "phone": client.phone,
                "status": st,
                "is_connected": client.is_connected,
                "device_model": client.fingerprint.device_model,
                "proxy_configured": client.proxy_config is not None,
            })

        return {
            "total_accounts": len(self._clients),
            "status_summary": status_counts,
            "clients": client_details,
        }

    def _start_health_monitor(self) -> None:
        """Starts background watchdog task for automatic reconnections."""
        if not self._monitor_task or self._monitor_task.done():
            self._is_running = True
            self._monitor_task = asyncio.create_task(self._health_monitor_loop())

    async def _health_monitor_loop(self) -> None:
        """Periodic loop to probe connections and trigger automatic recovery."""
        while self._is_running:
            try:
                await asyncio.sleep(30)
                for client in list(self._clients.values()):
                    if client.status == AccountStatus.ACTIVE and not client.is_connected:
                        logger.warning(
                            f"Account {client.account_id} disconnected unexpectedly. Triggering reconnect..."
                        )
                        asyncio.create_task(client.connect())
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in MTProto pool health monitor: {exc}", exc_info=True)
