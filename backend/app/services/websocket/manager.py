import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from uuid import UUID
from fastapi import WebSocket
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Manages active TMA WebSocket connections, handles chat channel subscriptions,
    and bridges Redis Pub/Sub chat updates to front-end clients in real time.
    """

    _instance: Optional["WebSocketConnectionManager"] = None

    def __init__(self) -> None:
        # Maps "account_id:peer_id" -> Set[WebSocket]
        self._chat_subscribers: Dict[str, Set[WebSocket]] = {}
        # Maps WebSocket -> subscribed "account_id:peer_id"
        self._connection_map: Dict[WebSocket, Optional[str]] = {}
        self._lock = asyncio.Lock()
        self._listener_task: Optional[asyncio.Task] = None

    @classmethod
    def get_instance(cls) -> "WebSocketConnectionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts and registers a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connection_map[websocket] = None
        logger.debug("WebSocket client connected.")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Cleans up disconnected WebSocket."""
        async with self._lock:
            current_chat = self._connection_map.pop(websocket, None)
            if current_chat and current_chat in self._chat_subscribers:
                self._chat_subscribers[current_chat].discard(websocket)
                if not self._chat_subscribers[current_chat]:
                    del self._chat_subscribers[current_chat]
        logger.debug("WebSocket client disconnected.")

    async def subscribe_chat(
        self,
        websocket: WebSocket,
        account_id: UUID | str,
        peer_id: int | str,
    ) -> None:
        """Binds a WebSocket connection to a specific chat dialogue for real-time updates."""
        chat_key = f"{account_id}:{peer_id}"
        async with self._lock:
            # Remove previous subscription if any
            old_chat = self._connection_map.get(websocket)
            if old_chat and old_chat in self._chat_subscribers:
                self._chat_subscribers[old_chat].discard(websocket)

            # Assign new chat subscription
            self._connection_map[websocket] = chat_key
            if chat_key not in self._chat_subscribers:
                self._chat_subscribers[chat_key] = set()
            self._chat_subscribers[chat_key].add(websocket)

        logger.debug(f"WebSocket client subscribed to chat {chat_key}")

    async def broadcast_to_chat(
        self,
        account_id: UUID | str,
        peer_id: int | str,
        message: Dict[str, Any],
    ) -> None:
        """Directly sends a JSON payload to all active WebSockets viewing this chat."""
        chat_key = f"{account_id}:{peer_id}"
        async with self._lock:
            sockets = list(self._chat_subscribers.get(chat_key, []))

        dead_sockets = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.warning(f"Error broadcasting to WebSocket: {exc}")
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for dead in dead_sockets:
                    await self.disconnect(dead)

    def start_redis_bridge(self, redis_client: Redis) -> None:
        """Launches the background listener consuming 'channel:chat:*' Pub/Sub broadcasts."""
        if not self._listener_task or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._redis_pubsub_listener(redis_client))

    async def _redis_pubsub_listener(self, redis_client: Redis) -> None:
        """Consumes pattern subscriptions and fans out to relevant WebSocket subscribers."""
        pubsub = redis_client.pubsub()
        await pubsub.psubscribe("channel:chat:*")
        logger.info("WebSocket Redis Pub/Sub bridge subscribed to 'channel:chat:*'")

        try:
            async for msg in pubsub.listen():
                if msg["type"] != "pmessage":
                    continue

                try:
                    channel = msg["channel"].decode("utf-8") if isinstance(msg["channel"], bytes) else msg["channel"]
                    # Channel format: channel:chat:{account_id}:{peer_id}
                    parts = channel.split(":")
                    if len(parts) >= 4:
                        account_id = parts[2]
                        peer_id = parts[3]

                        raw_data = msg["data"]
                        data_str = raw_data.decode("utf-8") if isinstance(raw_data, bytes) else raw_data
                        payload = json.loads(data_str)

                        await self.broadcast_to_chat(account_id, peer_id, payload)

                except Exception as exc:
                    logger.error(f"Error in WebSocket Redis bridge: {exc}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("WebSocket Redis bridge task cancelled.")
        finally:
            await pubsub.punsubscribe("channel:chat:*")
            await pubsub.close()
