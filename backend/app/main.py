import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from backend.app.core.config import settings
from backend.app.db.session import engine, async_session_factory
from backend.app.db.base import Base
from backend.app.services.mtproto.pool_manager import MTProtoPoolManager
from backend.app.services.events.consumer import InboundEventConsumer
from backend.app.services.events.pipeline import attach_inbound_pipeline
from backend.app.services.proxy.failover import ProxyFailoverMonitor
from backend.app.services.websocket.manager import WebSocketConnectionManager
from backend.app.api.v1.router import api_v1_router
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("StudioCRM")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifecycle manager for the FastAPI application: initializes database tables,
    Redis stream consumer, WebSocket bridge, MTProto pool manager, and proxy watchdog.
    """
    logger.info("Initializing StudioCRM backend...")

    # 1. Database table check/creation
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Redis Client & Inbound Event Consumer
    redis_client = Redis.from_url(settings.REDIS_URL)
    app.state.redis = redis_client

    consumer = InboundEventConsumer(
        redis_client=redis_client,
        session_factory=async_session_factory,
    )
    await consumer.start()
    app.state.consumer = consumer

    # 3. WebSocket Real-Time Bridge
    ws_manager = WebSocketConnectionManager.get_instance()
    ws_manager.start_redis_bridge(redis_client)

    # 4. MTProto Multi-Account Pool
    pool = MTProtoPoolManager.get_instance()
    attach_inbound_pipeline(pool, redis_client)

    async with async_session_factory() as session:
        try:
            await pool.initialize_from_db(session)
        except Exception as exc:
            logger.warning(f"Could not initialize MTProto pool from DB on startup: {exc}")

    # 5. Proxy Failover Watchdog
    proxy_monitor = ProxyFailoverMonitor(
        session_factory=async_session_factory,
        pool_manager=pool,
        check_interval_seconds=60,
    )
    await proxy_monitor.start()
    app.state.proxy_monitor = proxy_monitor

    logger.info("StudioCRM backend fully initialized.")

    yield

    # Shutdown sequence
    logger.info("Shutting down StudioCRM backend...")
    await proxy_monitor.stop()
    await consumer.stop()
    await pool.stop_all()
    await redis_client.close()
    await engine.dispose()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    """Factory function creating the FastAPI app."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        lifespan=lifespan,
    )

    # CORS configuration for Telegram Mini App and Server 1 Frontend
    cors_origins = ["*"]
    if settings.FRONTEND_ORIGIN_DOMAIN and settings.FRONTEND_ORIGIN_DOMAIN != "*":
        for d in [item.strip() for item in settings.FRONTEND_ORIGIN_DOMAIN.split(",") if item.strip()]:
            if not d.startswith("http://") and not d.startswith("https://"):
                cors_origins.extend([f"https://{d}", f"http://{d}"])
            else:
                cors_origins.append(d)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API v1 router (includes REST and /ws)
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # Mount static frontend for Telegram Mini App
    try:
        app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
    except Exception as exc:
        logger.warning(f"Could not mount static frontend at /app: {exc}")

    # Mount media cache for photos, voice notes, and documents
    try:
        from backend.app.services.events.producer import MEDIA_CACHE_DIR
        app.mount("/media", StaticFiles(directory=MEDIA_CACHE_DIR), name="media")
    except Exception as exc:
        logger.warning(f"Could not mount media cache at /media: {exc}")

    @app.get("/api/health", tags=["Health"])
    async def health_check() -> dict:
        pool = MTProtoPoolManager.get_instance()
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "pool_status": pool.get_pool_status(),
        }

    return app


app = create_app()
