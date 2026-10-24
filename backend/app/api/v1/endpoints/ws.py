import json
import logging
from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import async_session_factory
from backend.app.models.dialogue import Dialogue
from backend.app.services.mtproto.pool_manager import MTProtoPoolManager
from backend.app.services.outbound_dispatcher import OutboundDispatcher
from backend.app.services.websocket.manager import WebSocketConnectionManager

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/ws")
async def websocket_chat_gateway(websocket: WebSocket) -> None:
    """
    Bi-directional WebSocket connection for TMA clients.
    Handles real-time chat subscriptions, outbound message sending, and mark-as-read acknowledgments.
    """
    manager = WebSocketConnectionManager.get_instance()
    pool = MTProtoPoolManager.get_instance()
    dispatcher = OutboundDispatcher(pool_manager=pool)

    await manager.connect(websocket)

    try:
        while True:
            data_raw = await websocket.receive_text()
            try:
                msg: Dict[str, Any] = json.loads(data_raw)
            except Exception:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format."})
                continue

            action = msg.get("action")

            # 1. Ping / Pong Heartbeat
            if action == "ping":
                await websocket.send_json({"type": "pong"})

            # 2. Subscribe to Chat
            elif action == "subscribe_chat":
                account_id = msg.get("account_id")
                peer_id = msg.get("peer_id")
                if not account_id or not peer_id:
                    await websocket.send_json({"type": "error", "message": "account_id and peer_id required."})
                    continue

                await manager.subscribe_chat(websocket, account_id, peer_id)
                await websocket.send_json({
                    "type": "subscribed",
                    "account_id": str(account_id),
                    "peer_id": peer_id,
                })

            # 3. Send Outbound Message
            elif action == "send_message":
                account_id_str = msg.get("account_id")
                peer_id = msg.get("peer_id")
                text = msg.get("text")
                temp_id = msg.get("temp_id")

                if not account_id_str or not peer_id or not text:
                    await websocket.send_json({
                        "type": "error",
                        "temp_id": temp_id,
                        "message": "account_id, peer_id, and text are required to send message.",
                    })
                    continue

                try:
                    account_id = UUID(str(account_id_str))
                    async with async_session_factory() as session:
                        result = await dispatcher.dispatch(
                            session=session,
                            account_id=account_id,
                            peer_id=int(peer_id),
                            text=str(text),
                            temp_id=temp_id,
                        )

                    # Send immediate delivery confirmation back to sender
                    await websocket.send_json({
                        "type": "message_delivered",
                        **result,
                    })

                except PermissionError as exc:
                    await websocket.send_json({
                        "type": "send_failed",
                        "temp_id": temp_id,
                        "error": "ACCOUNT_BANNED_READ_ONLY",
                        "message": "Этот аккаунт заблокирован в Telegram. Доступен режим архива (только чтение).",
                    })
                except Exception as exc:
                    logger.error(f"Failed to dispatch message via WS: {exc}", exc_info=True)
                    await websocket.send_json({
                        "type": "send_failed",
                        "temp_id": temp_id,
                        "error": str(exc),
                    })

            # 4. Mark Chat as Read
            elif action == "mark_read":
                account_id_str = msg.get("account_id")
                peer_id = msg.get("peer_id")
                if account_id_str and peer_id:
                    try:
                        acc_id = UUID(str(account_id_str))
                        p_id = int(peer_id)
                        # Reset unread in database
                        async with async_session_factory() as session:
                            async with session.begin():
                                from sqlalchemy import update
                                await session.execute(
                                    update(Dialogue)
                                    .where(Dialogue.account_id == acc_id, Dialogue.peer_id == p_id)
                                    .values(unread_count=0)
                                )

                        # Trigger Telethon read acknowledge
                        client = pool.get_client(acc_id)
                        if client and client.is_connected:
                            await client.client.send_read_acknowledge(p_id)

                        await websocket.send_json({
                            "type": "read_acknowledged",
                            "account_id": str(acc_id),
                            "peer_id": p_id,
                        })
                    except Exception as exc:
                        logger.warning(f"Error marking read via WS: {exc}")

            # 5. Send Typing Status to Cloud
            elif action == "send_typing":
                account_id_str = msg.get("account_id")
                peer_id = msg.get("peer_id")
                if account_id_str and peer_id:
                    try:
                        acc_id = UUID(str(account_id_str))
                        await dispatcher.send_typing(acc_id, int(peer_id))
                    except Exception as exc:
                        logger.debug(f"Could not forward typing to cloud: {exc}")

            # 6. Edit Existing Message
            elif action == "edit_message":
                account_id_str = msg.get("account_id")
                peer_id = msg.get("peer_id")
                tg_msg_id = msg.get("telegram_message_id")
                new_text = msg.get("new_text")

                if account_id_str and peer_id and tg_msg_id and new_text:
                    try:
                        acc_id = UUID(str(account_id_str))
                        async with async_session_factory() as session:
                            res = await dispatcher.edit_message(
                                session=session,
                                account_id=acc_id,
                                peer_id=int(peer_id),
                                telegram_message_id=int(tg_msg_id),
                                new_text=str(new_text),
                            )
                        # Broadcast edit to this client and others
                        await manager.broadcast_to_chat(acc_id, peer_id, {
                            "type": "message_edited",
                            **res,
                        })
                    except PermissionError:
                        await websocket.send_json({"type": "edit_failed", "error": "ACCOUNT_BANNED_READ_ONLY"})
                    except Exception as exc:
                        logger.error(f"Failed editing message via WS: {exc}")
                        await websocket.send_json({"type": "edit_failed", "error": str(exc)})

            # 7. Delete Message for Everyone (Revoke)
            elif action == "delete_message":
                account_id_str = msg.get("account_id")
                peer_id = msg.get("peer_id")
                tg_msg_id = msg.get("telegram_message_id")
                revoke = msg.get("revoke", True)

                if account_id_str and peer_id and tg_msg_id:
                    try:
                        acc_id = UUID(str(account_id_str))
                        async with async_session_factory() as session:
                            res = await dispatcher.delete_message(
                                session=session,
                                account_id=acc_id,
                                peer_id=int(peer_id),
                                telegram_message_id=int(tg_msg_id),
                                revoke=bool(revoke),
                            )
                        # Broadcast deletion to this client and others
                        await manager.broadcast_to_chat(acc_id, peer_id, {
                            "type": "messages_deleted",
                            **res,
                        })
                    except PermissionError:
                        await websocket.send_json({"type": "delete_failed", "error": "ACCOUNT_BANNED_READ_ONLY"})
                    except Exception as exc:
                        logger.error(f"Failed deleting message via WS: {exc}")
                        await websocket.send_json({"type": "delete_failed", "error": str(exc)})

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown action '{action}'"})

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as exc:
        logger.error(f"Unexpected WebSocket error: {exc}", exc_info=True)
        await manager.disconnect(websocket)
