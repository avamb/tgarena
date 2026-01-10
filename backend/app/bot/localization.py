"""
Localization Module for Telegram Bot

Handles multi-language support with Russian as default and English as fallback.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Localization data structure
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        # Start command
        "welcome": "Добро пожаловать в TG-Ticket-Agent! 🎫\n\nЯ помогу вам купить билеты на мероприятия.\n\nИспользуйте ссылку от агента для начала покупки билетов.",
        "welcome_with_agent": "Добро пожаловать в TG-Ticket-Agent! 🎫\n\nВы подключены к агенту: <b>{agent_name}</b>\n\nНажмите кнопку ниже, чтобы просмотреть доступные мероприятия.",

        # Buttons
        "btn_view_events": "📋 Посмотреть мероприятия",
        "btn_my_tickets": "🎫 Мои билеты",
        "btn_help": "❓ Помощь",
        "btn_buy_ticket": "🛒 Купить билет",
        "btn_next_event": "➡️ Следующее",
        "btn_prev_event": "⬅️ Предыдущее",
        "btn_back": "🔙 Назад",
        "btn_back_to_events": "📋 К списку мероприятий",

        # Events
        "no_events": "К сожалению, мероприятий пока нет.",
        "events_list_title": "📋 <b>Доступные мероприятия</b>\n\nСтраница {page} из {total_pages}:",
        "event_details": "<b>{name}</b>\n\n📅 Дата: {date}\n📍 Место: {venue}\n💰 Цена: от {min_price} до {max_price} ₽\n{age_restriction}{countdown}",

        # Countdown
        "countdown_label": "\n⏳ До начала: {countdown}",
        "countdown_days": "{count} дн.",
        "countdown_hours": "{count} ч.",
        "countdown_minutes": "{count} мин.",
        "countdown_started": "Уже началось!",
        "countdown_starting_soon": "Скоро начало!",
        "event_list_item": "{number}. <b>{name}</b>\n   📅 {date} | 💰 от {min_price} ₽",
        "btn_page_prev": "⬅️ Назад",
        "btn_page_next": "➡️ Вперед",
        "page_info": "Страница {page} из {total}",
        "btn_event_select": "🎫 {name}",
        "loading_events": "⏳ Загружаю мероприятия...",
        "error_fetching_events": "Не удалось загрузить мероприятия. Попробуйте позже.",
        "error_event_not_found": "Мероприятие не найдено.",
        "loading_event": "⏳ Загружаю информацию о мероприятии...",

        # Tickets
        "no_tickets": "У вас пока нет билетов.",
        "ticket_info": "🎫 <b>{event_name}</b>\n\n📅 {date}\n📍 {venue}\n🪑 {sector}, Ряд {row}, Место {seat}\n💰 {price} ₽",
        "btn_share_ticket": "📤 Поделиться билетом",

        # Order status notifications
        "order_new": "📝 <b>Заказ #{order_id} создан</b>\n\nОжидаем оплаты...\nСумма: {amount} ₽",
        "order_paid": "✅ <b>Заказ #{order_id} оплачен!</b>\n\nСумма: {amount} ₽\nВаши билеты будут отправлены в ближайшее время.",
        "order_cancelled": "❌ <b>Заказ #{order_id} отменён</b>",
        "order_refunded": "💸 <b>Возврат по заказу #{order_id}</b>\n\nСумма возврата: {amount} ₽",

        # Errors
        "error_general": "Произошла ошибка. Пожалуйста, попробуйте позже.",
        "error_no_agent": "Для покупки билетов используйте ссылку от агента.",
        "error_agent_not_found": "Агент не найден. Используйте корректную ссылку.",
        "error_agent_inactive": "Агент временно недоступен.",
        "error_seat_reserved": "К сожалению, это место уже занято. Пожалуйста, выберите другое место.",
        "error_seats_unavailable": "Выбранные места недоступны. Пожалуйста, обновите страницу и выберите снова.",
        "error_reservation_failed": "Не удалось забронировать места. Попробуйте позже.",
        "error_session_expired": "Сессия истекла. Пожалуйста, начните сначала.",
        "error_payment_failed": "Оплата не прошла. Ваши места были освобождены.",
        "error_order_cancelled": "Заказ отменён.",

        # Help
        "unknown_command": "Неизвестная команда. Используйте /help для списка команд.",
        "unknown_message": "Я не понимаю. Используйте /help для помощи.",
        "help_text": "🎫 <b>TG-Ticket-Agent - Помощь</b>\n\n<b>Как купить билеты:</b>\n1. Перейдите по ссылке от агента\n2. Выберите мероприятие\n3. Нажмите 'Купить билет'\n4. Выберите места в открывшемся окне\n5. Оплатите заказ\n\nБилеты будут отправлены вам в этот чат.\n\n<b>Команды:</b>\n/start - Начать\n/help - Показать это сообщение\n/tickets - Мои билеты",

        # Age restriction
        "age_0": "",
        "age_6": "👶 6+",
        "age_12": "🧒 12+",
        "age_16": "👦 16+",
        "age_18": "🔞 18+",
    },
    "en": {
        # Start command
        "welcome": "Welcome to TG-Ticket-Agent! 🎫\n\nI'll help you buy event tickets.\n\nUse the link from an agent to start purchasing tickets.",
        "welcome_with_agent": "Welcome to TG-Ticket-Agent! 🎫\n\nYou are connected to agent: <b>{agent_name}</b>\n\nClick the button below to view available events.",

        # Buttons
        "btn_view_events": "📋 View Events",
        "btn_my_tickets": "🎫 My Tickets",
        "btn_help": "❓ Help",
        "btn_buy_ticket": "🛒 Buy Ticket",
        "btn_next_event": "➡️ Next",
        "btn_prev_event": "⬅️ Previous",
        "btn_back": "🔙 Back",
        "btn_back_to_events": "📋 Back to Events",

        # Events
        "no_events": "Sorry, there are no events available at the moment.",
        "events_list_title": "📋 <b>Available Events</b>\n\nPage {page} of {total_pages}:",
        "event_details": "<b>{name}</b>\n\n📅 Date: {date}\n📍 Venue: {venue}\n💰 Price: {min_price} - {max_price} ₽\n{age_restriction}{countdown}",

        # Countdown
        "countdown_label": "\n⏳ Starts in: {countdown}",
        "countdown_days": "{count}d",
        "countdown_hours": "{count}h",
        "countdown_minutes": "{count}m",
        "countdown_started": "Started!",
        "countdown_starting_soon": "Starting soon!",
        "event_list_item": "{number}. <b>{name}</b>\n   📅 {date} | 💰 from {min_price} ₽",
        "btn_page_prev": "⬅️ Previous",
        "btn_page_next": "➡️ Next",
        "page_info": "Page {page} of {total}",
        "btn_event_select": "🎫 {name}",
        "loading_events": "⏳ Loading events...",
        "error_fetching_events": "Failed to load events. Please try again later.",
        "error_event_not_found": "Event not found.",
        "loading_event": "⏳ Loading event details...",

        # Tickets
        "no_tickets": "You don't have any tickets yet.",
        "ticket_info": "🎫 <b>{event_name}</b>\n\n📅 {date}\n📍 {venue}\n🪑 {sector}, Row {row}, Seat {seat}\n💰 {price} ₽",
        "btn_share_ticket": "📤 Share Ticket",

        # Order status notifications
        "order_new": "📝 <b>Order #{order_id} created</b>\n\nAwaiting payment...\nAmount: {amount} ₽",
        "order_paid": "✅ <b>Order #{order_id} paid!</b>\n\nAmount: {amount} ₽\nYour tickets will be sent shortly.",
        "order_cancelled": "❌ <b>Order #{order_id} cancelled</b>",
        "order_refunded": "💸 <b>Refund for order #{order_id}</b>\n\nRefund amount: {amount} ₽",

        # Errors
        "error_general": "An error occurred. Please try again later.",
        "error_no_agent": "To purchase tickets, please use the link from an agent.",
        "error_agent_not_found": "Agent not found. Please use a valid link.",
        "error_agent_inactive": "Agent is temporarily unavailable.",
        "error_seat_reserved": "Sorry, this seat is already taken. Please choose another seat.",
        "error_seats_unavailable": "Selected seats are no longer available. Please refresh and try again.",
        "error_reservation_failed": "Failed to reserve seats. Please try again later.",
        "error_session_expired": "Session expired. Please start again.",
        "error_payment_failed": "Payment failed. Your seats have been released.",
        "error_order_cancelled": "Order cancelled.",

        # Help
        "unknown_command": "Unknown command. Use /help for available commands.",
        "unknown_message": "I don't understand. Use /help for assistance.",
        "help_text": "🎫 <b>TG-Ticket-Agent - Help</b>\n\n<b>How to buy tickets:</b>\n1. Use the link from an agent\n2. Select an event\n3. Click 'Buy Ticket'\n4. Select seats in the opened window\n5. Complete payment\n\nTickets will be sent to this chat.\n\n<b>Commands:</b>\n/start - Start\n/help - Show this message\n/tickets - My tickets",

        # Age restriction
        "age_0": "",
        "age_6": "👶 6+",
        "age_12": "🧒 12+",
        "age_16": "👦 16+",
        "age_18": "🔞 18+",
    }
}


def get_user_language(language_code: Optional[str]) -> str:
    """
    Determine user's preferred language based on Telegram language code.

    Args:
        language_code: Telegram user's language code (e.g., 'ru', 'en', 'uk')

    Returns:
        'ru' for Russian speakers, 'en' for others
    """
    if language_code is None:
        return "ru"

    # Russian and related languages default to Russian
    russian_codes = ["ru", "be", "uk", "kk", "ky", "tg", "uz"]

    if language_code.lower() in russian_codes:
        return "ru"

    return "en"


def get_text(key: str, lang: str = "ru", **kwargs) -> str:
    """
    Get localized text by key.

    Args:
        key: Translation key
        lang: Language code ('ru' or 'en')
        **kwargs: Format arguments for the text

    Returns:
        Localized and formatted text
    """
    # Fall back to Russian if language not supported
    if lang not in TRANSLATIONS:
        lang = "ru"

    translations = TRANSLATIONS[lang]

    # Get text or fall back to English, then to key itself
    text = translations.get(key)
    if text is None:
        text = TRANSLATIONS["en"].get(key, key)

    # Format with provided arguments
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing format key {e} for translation '{key}'")

    return text


def get_age_restriction_text(age: int, lang: str = "ru") -> str:
    """
    Get age restriction text.

    Args:
        age: Age restriction value (0, 6, 12, 16, 18)
        lang: Language code

    Returns:
        Age restriction text or empty string
    """
    key = f"age_{age}"
    return get_text(key, lang)
