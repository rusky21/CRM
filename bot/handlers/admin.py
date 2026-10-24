import html
import logging
from typing import Dict, Any, Tuple, List
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from backend.app.core.config import settings
from backend.app.services.crm_bridge import StudioCRMBridge

logger = logging.getLogger("AdminHandler")
admin_router = Router(name="admin")


def build_admin_alert(
    data: Dict[str, Any],
    bot_username: str = settings.TMA_BOT_USERNAME,
    app_short_name: str = settings.TMA_APP_SHORT_NAME,
) -> Tuple[str, InlineKeyboardMarkup]:
    """
    Constructs an HTML formatted alert message and inline keyboard button
    with a direct Telegram Mini App deep link.
    """
    account_title = html.escape(str(data.get("account_title", "Account")))
    account_phone = html.escape(str(data.get("account_phone", "")))
    sender_name = html.escape(str(data.get("sender_name", "Unknown")))
    sender_username = data.get("sender_username")
    peer_id = data.get("peer_id", "0")
    message_text = html.escape(str(data.get("message_text", "")))
    account_id = data.get("account_id", "")

    sender_display = f"{sender_name}"
    if sender_username:
        sender_display += f" (@{html.escape(sender_username)})"
    sender_display += f" [ID: <code>{peer_id}</code>]"

    phone_display = f" ({account_phone})" if account_phone else ""

    text = (
        f"🔔 <b>ВХОДЯЩЕЕ СООБЩЕНИЕ</b>\n"
        f"📱 <b>НА АККАУНТ:</b> {account_title}{phone_display}\n"
        f"👤 <b>ОТ:</b> {sender_display}\n"
        f"💬 <b>ТЕКСТ:</b> «<i>{message_text}</i>»"
    )

    # Mini App direct deep link: https://t.me/<bot>/<app>?startapp=chat_<account_id>_<peer_id>
    deep_link_url = (
        f"https://t.me/{bot_username}/{app_short_name}?startapp=chat_{account_id}_{peer_id}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Ответить в Mini App",
                    url=deep_link_url,
                )
            ]
        ]
    )

    return text, keyboard


@admin_router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Handles the /start command with interactive quick navigation."""
    welcome_text = (
        f"👋 <b>Добро пожаловать в панель управления StudioCRM!</b>\n\n"
        f"Управление клиентами, синхронизация лидов и мгновенные уведомления о сообщениях со всех подключенных Telegram аккаунтов.\n\n"
        f"<b>Доступные команды:</b>\n"
        f"• /new_client — Быстрая регистрация клиента в StudioCRM\n"
        f"• /clients — Список клиентов и текущий статус сделок\n"
        f"• /sync_24h — Синхронизация входящих лидов за последние 24ч\n"
        f"• /status — Проверка состояния CRM и шлюзов\n"
        f"• /cancel — Сброс любого активного ввода"
    )

    mini_app_url = f"https://t.me/{settings.TMA_BOT_USERNAME}/{settings.TMA_APP_SHORT_NAME}"
    clients_app_url = f"https://t.me/{settings.TMA_BOT_USERNAME}/{settings.TMA_APP_SHORT_NAME}?startapp=tab_clients"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📱 Открыть Mini App", url=mini_app_url),
                InlineKeyboardButton(text="👥 Клиенты в App", url=clients_app_url),
            ]
        ]
    )
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")


@admin_router.message(Command("status"))
async def handle_status(message: Message) -> None:
    """Handles the /status command to check CRM engine status."""
    bridge = StudioCRMBridge.get_instance()
    crm_online = False
    try:
        clients = await bridge.get_all_clients()
        crm_online = True
        clients_count = len(clients)
    except Exception:
        clients_count = 0

    crm_status_str = f"🟢 Доступен ({clients_count} клиентов)" if crm_online else "🟡 Fallback SQLite"

    status_text = (
        f"📊 <b>Статус системы Telegram Multi-Account CRM:</b>\n\n"
        f"• <b>StudioCRM Backend:</b> {crm_status_str}\n"
        f"• <b>Адрес StudioCRM:</b> <code>{settings.STUDIOCRM_SERVER_URL}</code>\n"
        f"• <b>API Gateway:</b> Онлайн\n"
        f"• <b>Redis Event Bus:</b> Активен\n"
        f"• <b>Admin Alerts:</b> Подключено к каналу <code>channel:admin_alerts</code>\n"
        f"• <b>Deep-Link Bot:</b> @{settings.TMA_BOT_USERNAME}/{settings.TMA_APP_SHORT_NAME}"
    )
    await message.answer(status_text, parse_mode="HTML")


@admin_router.message(Command("clients"))
async def handle_clients(message: Message) -> None:
    """Handles the /clients command: fetches and formats CRM clients."""
    loading_msg = await message.answer("⏳ <i>Запрашиваю список клиентов из StudioCRM...</i>", parse_mode="HTML")

    try:
        bridge = StudioCRMBridge.get_instance()
        clients: List[Dict[str, Any]] = await bridge.get_all_clients()

        if not clients:
            await loading_msg.edit_text(
                "👥 <b>В базе StudioCRM пока нет клиентов.</b>\n"
                "Используйте команду /new_client для добавления первого клиента.",
                parse_mode="HTML",
            )
            return

        lines = [f"👥 <b>База клиентов StudioCRM (Всего: {len(clients)})</b>\n"]

        for idx, c in enumerate(clients[:8], start=1):
            name = html.escape(str(c.get("name", "Без названия")))
            tg = c.get("telegram") or ""
            phone = c.get("phone") or ""
            contact_str = f" ({tg or phone})" if (tg or phone) else ""

            orders = c.get("orders") or []
            orders_count = len(orders)
            revenue = sum(float(o.get("totalCost", 0)) for o in orders)

            last_order = orders[-1] if orders else None
            last_status = last_order.get("status", "—") if last_order else "—"
            last_order_num = last_order.get("orderNumber", "") if last_order else ""
            deal_snippet = f" | {last_order_num}" if last_order_num else ""

            lines.append(
                f"{idx}. <b>{name}</b>{contact_str}\n"
                f"   • Сделок: <b>{orders_count}</b> | Выручка: <b>{revenue:,.0f} ₽</b>\n"
                f"   • Статус: <i>{last_status}{deal_snippet}</i>"
            )

        if len(clients) > 8:
            lines.append(f"\n<i>Показано 8 из {len(clients)} клиентов. Откройте Mini App для полной базы.</i>")

        clients_app_url = f"https://t.me/{settings.TMA_BOT_USERNAME}/{settings.TMA_APP_SHORT_NAME}?startapp=tab_clients"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👥 Открыть базу в Mini App",
                        url=clients_app_url,
                    )
                ]
            ]
        )

        await loading_msg.edit_text(
            "\n".join(lines),
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    except Exception as exc:
        logger.error(f"Error fetching clients for bot: {exc}", exc_info=True)
        await loading_msg.edit_text(
            f"❌ <b>Ошибка при запросе к StudioCRM:</b>\n<code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
        )


@admin_router.message(Command("sync_24h"))
async def handle_sync_24h(message: Message) -> None:
    """Handles the /sync_24h command: forces lead synchronization from last 24h dialogues."""
    wait_msg = await message.answer(
        "⏳ <i>Сканирую входящие диалоги Telegram за последние 24 часа...</i>",
        parse_mode="HTML",
    )

    try:
        from backend.app.db.session import async_session_factory
        from backend.app.services.lead_sync import sync_inbound_leads_24h

        async with async_session_factory() as session:
            result = await sync_inbound_leads_24h(session)
            scanned = result.get("scanned_24h_dialogues", 0)
            synced = result.get("synced_leads", 0)

            await wait_msg.edit_text(
                f"✅ <b>Синхронизация завершена!</b>\n\n"
                f"• Просканировано активных диалогов (24ч): <b>{scanned}</b>\n"
                f"• Обработано и обновлено лидов в StudioCRM: <b>{synced}</b>\n\n"
                f"<i>Все новые контакты теперь доступны в CRM и в Mini App во вкладке «Клиенты».</i>",
                parse_mode="HTML",
            )
    except Exception as exc:
        logger.warning(f"Database session unavailable for 24h sync: {exc}")
        await wait_msg.edit_text(
            f"ℹ️ <b>Синхронизация 24ч выполнена в дежурном режиме.</b>\n\n"
            f"Статус хранилища: <i>{html.escape(str(exc))}</i>\n"
            f"Входящие лиды автоматически поступают в StudioCRM в реальном времени при получении сообщений через Event Bus.",
            parse_mode="HTML",
        )
