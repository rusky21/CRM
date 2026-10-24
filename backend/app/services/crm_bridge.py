import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

try:
    import httpx
except ImportError:
    httpx = None

try:
    from backend.app.core.config import settings
    DEFAULT_SERVER_URL = settings.STUDIOCRM_SERVER_URL
    DEFAULT_SQLITE_PATH = settings.STUDIOCRM_SQLITE_PATH
except (ImportError, Exception):
    DEFAULT_SERVER_URL = os.getenv("STUDIOCRM_SERVER_URL", "http://212.67.15.218:5000")
    DEFAULT_SQLITE_PATH = os.getenv("STUDIOCRM_SQLITE_PATH", "studiocrm.db")

logger = logging.getLogger(__name__)


class StudioCRMBridge:
    """
    Bidirectional bridge connecting the Telegram Multi-Account CRM to the
    existing StudioCRM system (ASP.NET backend on port 5000 with local SQLite fallback).
    """

    _instance: Optional["StudioCRMBridge"] = None

    def __init__(
        self,
        server_url: str = DEFAULT_SERVER_URL,
        sqlite_path: str = DEFAULT_SQLITE_PATH,
        timeout: float = 6.0,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.sqlite_path = sqlite_path
        self.timeout = timeout

    @classmethod
    def get_instance(cls) -> "StudioCRMBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # =========================================================================
    # 1. CLIENTS API
    # =========================================================================

    async def get_all_clients(self) -> List[Dict[str, Any]]:
        """
        Fetches all clients from StudioCRM with their nested orders.
        Falls back to local SQLite if remote server is unreachable.
        """
        try:
            return await self._http_get(f"{self.server_url}/api/clients")
        except Exception as exc:
            logger.warning(
                f"StudioCRM remote server ({self.server_url}) unavailable: {exc}. "
                f"Falling back to local SQLite database ({self.sqlite_path})."
            )
            return await asyncio.to_thread(self._sqlite_get_all_clients)

    async def find_client_by_telegram(
        self, username: Optional[str] = None, phone: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Searches for an existing StudioCRM client by Telegram handle (@username) or phone number.
        """
        clients = await self.get_all_clients()
        clean_user = username.lstrip("@").lower() if username else None
        clean_phone = "".join(filter(str.isdigit, phone)) if phone else None

        for c in clients:
            tg = (c.get("telegram") or "").lstrip("@").lower()
            ph = "".join(filter(str.isdigit, c.get("phone") or ""))

            if clean_user and tg and clean_user == tg:
                return c
            if clean_phone and ph and clean_phone[-10:] == ph[-10:]:
                return c

        return None

    async def create_or_update_client(
        self,
        name: str,
        telegram: Optional[str] = None,
        phone: Optional[str] = None,
        notes: Optional[str] = None,
        contact_person: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates or updates a client record in StudioCRM.
        """
        clean_tg = f"@{telegram.lstrip('@')}" if telegram else None
        existing = await self.find_client_by_telegram(username=telegram, phone=phone)

        payload = {
            "name": name.strip(),
            "contactPerson": contact_person or name.strip(),
            "phone": phone or (existing.get("phone") if existing else None),
            "email": existing.get("email") if existing else None,
            "telegram": clean_tg or (existing.get("telegram") if existing else None),
            "notes": notes or (existing.get("notes") if existing else "Created via Telegram CRM integration"),
        }

        if existing and existing.get("id"):
            client_id = existing["id"]
            try:
                await self._http_put(f"{self.server_url}/api/clients/{client_id}", payload)
                payload["id"] = client_id
                payload["orders"] = existing.get("orders", [])
                return payload
            except Exception as exc:
                logger.warning(f"Remote update failed: {exc}, using SQLite fallback")
                return await asyncio.to_thread(self._sqlite_update_client, client_id, payload)
        else:
            try:
                res = await self._http_post(f"{self.server_url}/api/clients", payload)
                return res
            except Exception as exc:
                logger.warning(f"Remote create failed: {exc}, using SQLite fallback")
                return await asyncio.to_thread(self._sqlite_create_client, payload)

    # =========================================================================
    # 2. ORDERS / DEALS API
    # =========================================================================

    async def create_order(
        self,
        client_id: int,
        title: str,
        total_cost: float,
        deadline: Optional[str] = None,
        notes: Optional[str] = None,
        status: str = "New",
    ) -> Dict[str, Any]:
        """
        Creates an official order in StudioCRM linked to client_id.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "clientId": client_id,
            "title": title.strip(),
            "totalCost": float(total_cost),
            "status": status,
            "startDate": now_iso,
            "deadline": deadline,
            "notes": notes,
        }

        try:
            return await self._http_post(f"{self.server_url}/api/orders", payload)
        except Exception as exc:
            logger.warning(f"Remote create_order failed: {exc}, using SQLite fallback")
            return await asyncio.to_thread(self._sqlite_create_order, payload)

    async def get_orders_for_client(self, client_id: int) -> List[Dict[str, Any]]:
        """
        Returns all orders for a specific StudioCRM client ID.
        """
        try:
            clients = await self.get_all_clients()
            for c in clients:
                if c.get("id") == client_id:
                    return c.get("orders", [])
            return []
        except Exception:
            return await asyncio.to_thread(self._sqlite_get_orders_for_client, client_id)

    # =========================================================================
    # 3. HTTP HELPER METHODS
    # =========================================================================

    async def _http_get(self, url: str) -> Any:
        if httpx is not None:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                res.raise_for_status()
                return res.json()
        else:
            # Fallback using asyncio.to_thread with urllib
            return await asyncio.to_thread(self._urllib_request, url, method="GET")

    async def _http_post(self, url: str, data: Dict[str, Any]) -> Any:
        if httpx is not None:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=data)
                res.raise_for_status()
                return res.json()
        else:
            return await asyncio.to_thread(self._urllib_request, url, method="POST", data=data)

    async def _http_put(self, url: str, data: Dict[str, Any]) -> Any:
        if httpx is not None:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.put(url, json=data)
                res.raise_for_status()
                return res.json() if res.content else {}
        else:
            return await asyncio.to_thread(self._urllib_request, url, method="PUT", data=data)

    def _urllib_request(self, url: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Any:
        import urllib.request
        req = urllib.request.Request(url, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        body_bytes = json.dumps(data).encode("utf-8") if data else None
        with urllib.request.urlopen(req, data=body_bytes, timeout=self.timeout) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else {}

    # =========================================================================
    # 4. LOCAL SQLITE FALLBACK IMPLEMENTATION
    # =========================================================================

    def _get_sqlite_conn(self) -> sqlite3.Connection:
        if not os.path.exists(self.sqlite_path):
            raise FileNotFoundError(f"Local SQLite database not found at {self.sqlite_path}")
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _sqlite_get_all_clients(self) -> List[Dict[str, Any]]:
        with self._get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Clients ORDER BY Id DESC")
            client_rows = cursor.fetchall()

            cursor.execute("SELECT * FROM Orders ORDER BY Id DESC")
            order_rows = cursor.fetchall()

            orders_by_client: Dict[int, List[Dict[str, Any]]] = {}
            for o in order_rows:
                cid = o["ClientId"]
                if cid not in orders_by_client:
                    orders_by_client[cid] = []
                orders_by_client[cid].append({
                    "id": o["Id"],
                    "orderNumber": o["OrderNumber"],
                    "clientId": cid,
                    "title": o["Title"],
                    "status": "New" if o["Status"] == 0 else "InProgress" if o["Status"] == 1 else "Completed",
                    "totalCost": float(o["TotalCost"]) if o["TotalCost"] else 0.0,
                    "startDate": o["StartDate"],
                    "deadline": o["Deadline"],
                    "notes": o["Notes"],
                    "createdAt": o["CreatedAt"],
                })

            clients = []
            for c in client_rows:
                cid = c["Id"]
                clients.append({
                    "id": cid,
                    "name": c["Name"],
                    "contactPerson": c["ContactPerson"],
                    "phone": c["Phone"],
                    "email": c["Email"],
                    "telegram": c["Telegram"],
                    "notes": c["Notes"],
                    "createdAt": c["CreatedAt"],
                    "orders": orders_by_client.get(cid, []),
                })
            return clients

    def _sqlite_create_client(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._get_sqlite_conn() as conn:
            cursor = conn.cursor()
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO Clients (Name, ContactPerson, Phone, Email, Telegram, Notes, CreatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("name"),
                    payload.get("contactPerson"),
                    payload.get("phone"),
                    payload.get("email"),
                    payload.get("telegram"),
                    payload.get("notes"),
                    now_str,
                ),
            )
            conn.commit()
            new_id = cursor.lastrowid
            return {
                "id": new_id,
                "name": payload.get("name"),
                "contactPerson": payload.get("contactPerson"),
                "phone": payload.get("phone"),
                "email": payload.get("email"),
                "telegram": payload.get("telegram"),
                "notes": payload.get("notes"),
                "createdAt": now_str,
                "orders": [],
            }

    def _sqlite_update_client(self, client_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE Clients
                SET Name = ?, ContactPerson = ?, Phone = ?, Email = ?, Telegram = ?, Notes = ?
                WHERE Id = ?
                """,
                (
                    payload.get("name"),
                    payload.get("contactPerson"),
                    payload.get("phone"),
                    payload.get("email"),
                    payload.get("telegram"),
                    payload.get("notes"),
                    client_id,
                ),
            )
            conn.commit()
            payload["id"] = client_id
            return payload

    def _sqlite_create_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._get_sqlite_conn() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc)
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("SELECT COUNT(*) FROM Orders")
            count = cursor.fetchone()[0] + 1
            order_number = f"ORD-{now.year}-{count:03d}"

            status_int = 0
            if payload.get("status") == "InProgress":
                status_int = 1
            elif payload.get("status") == "Completed":
                status_int = 2

            cursor.execute(
                """
                INSERT INTO Orders (
                    OrderNumber, ClientId, Title, Status, TotalCost, StartDate, Deadline, Notes, CreatedAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_number,
                    payload["clientId"],
                    payload["title"],
                    status_int,
                    str(payload["totalCost"]),
                    payload.get("startDate") or now_str,
                    payload.get("deadline"),
                    payload.get("notes"),
                    now_str,
                ),
            )
            conn.commit()
            new_id = cursor.lastrowid
            return {
                "id": new_id,
                "orderNumber": order_number,
                "clientId": payload["clientId"],
                "title": payload["title"],
                "status": payload.get("status", "New"),
                "totalCost": payload["totalCost"],
                "startDate": payload.get("startDate") or now_str,
                "deadline": payload.get("deadline"),
                "notes": payload.get("notes"),
                "createdAt": now_str,
                "paidAmount": 0,
                "remainingDebt": payload["totalCost"],
                "progressPercentage": 0,
            }

    def _sqlite_get_orders_for_client(self, client_id: int) -> List[Dict[str, Any]]:
        with self._get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Orders WHERE ClientId = ? ORDER BY Id DESC", (client_id,))
            rows = cursor.fetchall()
            return [
                {
                    "id": o["Id"],
                    "orderNumber": o["OrderNumber"],
                    "clientId": o["ClientId"],
                    "title": o["Title"],
                    "status": "New" if o["Status"] == 0 else "InProgress",
                    "totalCost": float(o["TotalCost"]) if o["TotalCost"] else 0.0,
                    "startDate": o["StartDate"],
                    "deadline": o["Deadline"],
                    "notes": o["Notes"],
                    "createdAt": o["CreatedAt"],
                }
                for o in rows
            ]
