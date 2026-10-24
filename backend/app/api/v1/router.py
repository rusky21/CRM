from fastapi import APIRouter
from backend.app.api.v1.endpoints.accounts import router as accounts_router
from backend.app.api.v1.endpoints.dialogues import router as dialogues_router
from backend.app.api.v1.endpoints.messages import router as messages_router
from backend.app.api.v1.endpoints.orders import router as orders_router
from backend.app.api.v1.endpoints.clients import router as clients_router
from backend.app.api.v1.endpoints.ws import ws_router

api_v1_router = APIRouter()

# Mount REST endpoints
api_v1_router.include_router(accounts_router)
api_v1_router.include_router(dialogues_router)
api_v1_router.include_router(messages_router)
api_v1_router.include_router(orders_router)
api_v1_router.include_router(clients_router)

# Mount WebSocket endpoint
api_v1_router.include_router(ws_router)
