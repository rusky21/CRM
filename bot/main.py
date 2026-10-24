import asyncio
import json
import logging
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand
from redis.asyncio import Redis

# Ensure root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.services.events.consumer import ADMIN_ALERTS_CHANNEL
from bot.handlers.admin import admin_router, build_admin_alert
from bot.handlers.client_intake import client_intake_router

logger = logging.getLogger("AdminAlertBot")


async def setup_bot_commands(bot: Bot) -> None:
    """Configures the official Telegram Bot Menu commands list."""
    commands = [
        BotCommand(command="start", description="Запуск панели управления"),
        BotCommand(command="status", description="Статус подключенных аккаунтов"),
        BotCommand(command="new_client", description="Быстрая запись клиента в StudioCRM"),
        BotCommand(command="clients", description="Список клиентов из CRM"),
        BotCommand(command="sync_24h", description="Принудительная синхронизация лидов за 24ч"),
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Successfully registered bot menu commands.")
    except Exception as exc:
        logger.warning(f"Failed to set bot commands menu: {exc}")


async def listen_admin_alerts(bot: Bot, redis_client: Redis) -> None:
    """
    Subscribes to Redis Pub/Sub channel 'channel:admin_alerts'
    and dispatches push notifications to the administrator chat with TMA deep-link.
    """
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(ADMIN_ALERTS_CHANNEL)
    logger.info(f"Subscribed to Redis alert channel: {ADMIN_ALERTS_CHANNEL}")

    target_chat_id = settings.ADMIN_CHAT_ID
    if not target_chat_id:
        logger.warning("ADMIN_CHAT_ID is not configured in settings. Alerts will not be sent to Telegram.")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                raw_data = message["data"]
                data_str = raw_data.decode("utf-8") if isinstance(raw_data, bytes) else raw_data
                data = json.loads(data_str)

                if target_chat_id:
                    text, keyboard = build_admin_alert(data)
                    await bot.send_message(
                        chat_id=target_chat_id,
                        text=text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML,
                    )
                    logger.debug(f"Admin alert delivered for peer_id {data.get('peer_id')}")

            except Exception as exc:
                logger.error(f"Failed processing alert in bot listener: {exc}", exc_info=True)

    except asyncio.CancelledError:
        logger.info("Admin alert listener task cancelled.")
    finally:
        await pubsub.unsubscribe(ADMIN_ALERTS_CHANNEL)
        await pubsub.close()


async def start_bot() -> None:
    """Launches the Admin Alert Bot and Pub/Sub listener."""
    if not settings.ADMIN_BOT_TOKEN:
        raise ValueError("ADMIN_BOT_TOKEN is not configured in settings or .env file.")

    bot = Bot(
        token=settings.ADMIN_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(client_intake_router)

    # Register Bot Menu Commands
    await setup_bot_commands(bot)

    redis_client = Redis.from_url(settings.REDIS_URL)

    # Spawn background alert listener
    alert_task = asyncio.create_task(listen_admin_alerts(bot, redis_client))

    # Clear any active webhook to prevent TelegramConflictError during long-polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Cleared previous webhook (if any) and reset pending updates.")
    except Exception as exc:
        logger.warning(f"Could not reset webhook: {exc}")

    logger.info("Admin Alert Bot starting long-polling...")
    try:
        await dp.start_polling(bot)
    except Exception as exc:
        logger.error(f"Fatal error during bot polling: {exc}", exc_info=True)
        raise
    finally:
        alert_task.cancel()
        await alert_task
        await redis_client.close()
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_bot())
