import html
import logging
import re
from typing import Optional, Tuple, Dict, Any

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from backend.app.core.config import settings
from backend.app.services.crm_bridge import StudioCRMBridge

logger = logging.getLogger("ClientIntakeFSM")

client_intake_router = Router(name="client_intake")


class ClientIntakeStates(StatesGroup):
    """FSM states for interactive client intake and immediate deal creation."""
    name = State()
    telegram_or_phone = State()
    contact_person = State()
    notes = State()
    order_info = State()


def parse_contact_input(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts Telegram handle and/or phone number from freeform user text.
    Returns (telegram_handle, phone_number).
    """
    raw = raw.strip()
    tg: Optional[str] = None
    phone: Optional[str] = None

    # Match @username or t.me/username
    tg_match = re.search(r"@([A-Za-z0-9_]{3,32})|t\.me/([A-Za-z0-9_]{3,32})", raw)
    if tg_match:
        uname = tg_match.group(1) or tg_match.group(2)
        tg = f"@{uname}"

    # Match phone numbers (must contain at least 7 digits)
    digits = re.sub(r"[^\d+]", "", raw)
    if len(re.sub(r"\D", "", digits)) >= 7:
        phone = digits

    # Fallback heuristics
    if not tg and not phone:
        if raw.startswith("@") or (" " not in raw and not any(ch.isdigit() for ch in raw)):
            tg = f"@{raw.lstrip('@')}"
        else:
            phone = raw

    return tg, phone


def parse_order_input(text: str) -> Optional[Tuple[float, str]]:
    """
    Parses amount and deal title from text like '75000 Разработка Telegram-бота'.
    Returns (amount, title) or None if skipped.
    """
    text = text.strip()
    if text.lower() == "/skip":
        return None

    # Pattern: leading number (with spaces/commas) followed by optional currency and title
    match = re.match(r"^([\d\s]+(?:[.,]\d+)?)\s*(?:₽|руб|rub|usd|\$)?\s+(.+)$", text, re.IGNORECASE)
    if match:
        amount_str = re.sub(r"\s+", "", match.group(1)).replace(",", ".")
        try:
            amount = float(amount_str)
            title = match.group(2).strip()
            return amount, title
        except ValueError:
            pass

    # Fallback: extract first number found and use remaining text as title
    digits_match = re.search(r"(\d+(?:[.,]\d+)?)", text)
    if digits_match:
        try:
            amt = float(digits_match.group(1).replace(",", "."))
            title = text.replace(digits_match.group(1), "").strip() or "Новая сделка"
            return amt, title
        except ValueError:
            pass

    return 0.0, text


# =========================================================================
# FSM HANDLERS
# =========================================================================

@client_intake_router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext) -> None:
    """Cancels active client intake FSM at any step."""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer(
            "❌ <b>Регистрация клиента отменена.</b>\n"
            "Вы можете начать заново командой /new_client.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await message.answer("ℹ️ В данный момент нет активного процесса регистрации клиента.")


@client_intake_router.message(Command("new_client"))
@client_intake_router.message(Command("add_client"))
async def start_client_intake(message: Message, state: FSMContext) -> None:
    """Initiates interactive FSM for client registration."""
    await state.clear()
    await state.set_state(ClientIntakeStates.name)

    intro_text = (
        "👤 <b>Добавление нового клиента в StudioCRM</b>\n\n"
        "<b>Шаг 1 из 5:</b> Введите название компании или имя клиента:\n"
        "<i>(например: ООО «ТехноПром Инжиниринг» или Иван Петров)</i>\n\n"
        "<i>Для отмены в любой момент отправьте /cancel</i>"
    )
    await message.answer(intro_text, parse_mode="HTML")


@client_intake_router.message(ClientIntakeStates.name, F.text)
async def process_client_name(message: Message, state: FSMContext) -> None:
    """Handles Step 1: Client / Company Name."""
    name = (message.text or "").strip()
    if name.lower() == "/skip" or len(name) < 2:
        await message.answer(
            "⚠️ <b>Название компании или имя обязательно.</b>\n"
            "Пожалуйста, введите корректное название:",
            parse_mode="HTML",
        )
        return

    await state.update_data(name=name)
    await state.set_state(ClientIntakeStates.telegram_or_phone)

    prompt = (
        f"<b>Шаг 2 из 5:</b> Введите Telegram (@username) или номер телефона клиента:\n"
        f"<i>(например: @client_ceo или +7 999 123-45-67)</i>"
    )
    await message.answer(prompt, parse_mode="HTML")


@client_intake_router.message(ClientIntakeStates.telegram_or_phone, F.text)
async def process_contact(message: Message, state: FSMContext) -> None:
    """Handles Step 2: Telegram handle or phone number."""
    raw_contact = (message.text or "").strip()
    tg, phone = parse_contact_input(raw_contact)

    await state.update_data(
        telegram=tg,
        phone=phone,
        raw_contact=raw_contact,
    )
    await state.set_state(ClientIntakeStates.contact_person)

    prompt = (
        f"<b>Шаг 3 из 5:</b> Контактное лицо (ФИО / должность):\n"
        f"<i>(или нажмите /skip, чтобы пропустить)</i>"
    )
    await message.answer(prompt, parse_mode="HTML")


@client_intake_router.message(ClientIntakeStates.contact_person, F.text)
async def process_contact_person(message: Message, state: FSMContext) -> None:
    """Handles Step 3: Contact person."""
    text = (message.text or "").strip()
    contact_person = None if text.lower() == "/skip" else text

    await state.update_data(contact_person=contact_person)
    await state.set_state(ClientIntakeStates.notes)

    prompt = (
        f"<b>Шаг 4 из 5:</b> Заметки / комментарий к клиенту:\n"
        f"<i>(или нажмите /skip, чтобы пропустить)</i>"
    )
    await message.answer(prompt, parse_mode="HTML")


@client_intake_router.message(ClientIntakeStates.notes, F.text)
async def process_notes(message: Message, state: FSMContext) -> None:
    """Handles Step 4: Notes and comments."""
    text = (message.text or "").strip()
    notes = "Зарегистрирован через Telegram Bot (/new_client)" if text.lower() == "/skip" else f"{text} [via Bot]"

    await state.update_data(notes=notes)
    await state.set_state(ClientIntakeStates.order_info)

    prompt = (
        "<b>Шаг 5 из 5:</b> Хотите сразу создать сделку в StudioCRM?\n\n"
        "Введите <b>сумму и название</b> (например: <code>75000 Разработка Telegram-бота</code>)\n"
        "<i>или нажмите /skip, чтобы завершить без сделки:</i>"
    )
    await message.answer(prompt, parse_mode="HTML")


@client_intake_router.message(ClientIntakeStates.order_info, F.text)
async def process_order_info(message: Message, state: FSMContext) -> None:
    """Handles Step 5: Order information and submits client to StudioCRM."""
    order_raw = (message.text or "").strip()
    order_data = parse_order_input(order_raw)

    data = await state.get_data()
    name = data["name"]
    telegram = data.get("telegram")
    phone = data.get("phone")
    contact_person = data.get("contact_person")
    notes = data.get("notes")

    status_msg = await message.answer(
        "⏳ <i>Сохраняю данные клиента в StudioCRM...</i>",
        parse_mode="HTML",
    )

    try:
        bridge = StudioCRMBridge.get_instance()
        client_res = await bridge.create_or_update_client(
            name=name,
            telegram=telegram,
            phone=phone,
            notes=notes,
            contact_person=contact_person,
        )
        client_id = client_res.get("id")

        order_res: Optional[Dict[str, Any]] = None
        order_number: Optional[str] = None
        if order_data and client_id:
            amount, order_title = order_data
            order_res = await bridge.create_order(
                client_id=int(client_id),
                title=order_title,
                total_cost=amount,
                notes="Создано через Telegram Bot FSM (/new_client)",
            )
            order_number = order_res.get("orderNumber") or f"ORD-2026-{order_res.get('id', 'NEW')}"

        # Clear FSM State
        await state.clear()

        # Build Rich Confirmation Card
        card_lines = [
            "✅ <b>Клиент успешно зарегистрирован в StudioCRM!</b>\n",
            f"👤 <b>Клиент:</b> {html.escape(name)}",
        ]
        if contact_person:
            card_lines.append(f"👤 <b>Контакт:</b> {html.escape(contact_person)}")

        contact_parts = []
        if telegram:
            contact_parts.append(f"💬 <b>Telegram:</b> {html.escape(telegram)}")
        if phone:
            contact_parts.append(f"📞 <b>Тел:</b> {html.escape(phone)}")
        if contact_parts:
            card_lines.append(" | ".join(contact_parts))

        if order_data and order_number:
            amount, order_title = order_data
            card_lines.append(
                f"💼 <b>Сделка:</b> <code>{html.escape(order_number)}</code> "
                f"({amount:,.0f} ₽) — {html.escape(order_title)}"
            )
        else:
            card_lines.append("💼 <b>Сделка:</b> <i>Не создана</i>")

        if notes:
            card_lines.append(f"📝 <b>Заметки:</b> {html.escape(notes)}")

        confirmation_text = "\n".join(card_lines)

        deep_link_url = (
            f"https://t.me/{settings.TMA_BOT_USERNAME}/{settings.TMA_APP_SHORT_NAME}?startapp=tab_clients"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👥 Посмотреть в Mini App",
                        url=deep_link_url,
                    )
                ]
            ]
        )

        await status_msg.edit_text(
            confirmation_text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    except Exception as exc:
        logger.error(f"Failed to persist client in StudioCRM: {exc}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Ошибка при сохранении в StudioCRM:</b>\n"
            f"<code>{html.escape(str(exc))}</code>\n\n"
            f"Попробуйте повторить команду /new_client.",
            parse_mode="HTML",
        )
