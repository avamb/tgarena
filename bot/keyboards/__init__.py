"""
Bot Keyboards Module

Inline keyboard builders for the Telegram bot.
Provides system buttons (inline keyboards) instead of text-based commands.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    """Get main menu inline keyboard.

    Args:
        lang: Language code ('ru' or 'en')

    Returns:
        InlineKeyboardMarkup with main menu buttons
    """
    texts = {
        "ru": {
            "events": "🎭 Мероприятия",
            "my_tickets": "🎫 Мои билеты",
            "help": "❓ Помощь",
            "language": "🌐 Язык",
        },
        "en": {
            "events": "🎭 Events",
            "my_tickets": "🎫 My Tickets",
            "help": "❓ Help",
            "language": "🌐 Language",
        },
    }

    t = texts.get(lang, texts["en"])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t["events"], callback_data="menu:events"),
                InlineKeyboardButton(text=t["my_tickets"], callback_data="menu:mytickets"),
            ],
            [
                InlineKeyboardButton(text=t["help"], callback_data="menu:help"),
                InlineKeyboardButton(text=t["language"], callback_data="menu:language"),
            ],
        ]
    )
    return keyboard


def get_events_navigation_keyboard(
    lang: str = "en",
    has_prev: bool = False,
    has_next: bool = False,
    event_id: int | None = None,
) -> InlineKeyboardMarkup:
    """Get events navigation keyboard.

    Args:
        lang: Language code ('ru' or 'en')
        has_prev: Whether previous event exists
        has_next: Whether next event exists
        event_id: Current event ID for buy button

    Returns:
        InlineKeyboardMarkup with event navigation buttons
    """
    texts = {
        "ru": {
            "prev": "⬅️ Пред.",
            "next": "След. ➡️",
            "buy": "🎫 Купить билет",
            "list": "📋 Список",
            "back": "🔙 Назад",
        },
        "en": {
            "prev": "⬅️ Prev",
            "next": "Next ➡️",
            "buy": "🎫 Buy Ticket",
            "list": "📋 List",
            "back": "🔙 Back",
        },
    }

    t = texts.get(lang, texts["en"])

    # Navigation row
    nav_buttons = []
    if has_prev:
        nav_buttons.append(InlineKeyboardButton(text=t["prev"], callback_data="nav:prev_event"))
    nav_buttons.append(InlineKeyboardButton(text=t["list"], callback_data="nav:event_list"))
    if has_next:
        nav_buttons.append(InlineKeyboardButton(text=t["next"], callback_data="nav:next_event"))

    # Buy and back row
    action_buttons = []
    if event_id:
        action_buttons.append(
            InlineKeyboardButton(text=t["buy"], callback_data=f"event:buy:{event_id}")
        )
    action_buttons.append(InlineKeyboardButton(text=t["back"], callback_data="nav:main_menu"))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            nav_buttons,
            action_buttons,
        ]
    )
    return keyboard


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Get language selection keyboard.

    Returns:
        InlineKeyboardMarkup with language selection buttons
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            ],
            [
                InlineKeyboardButton(text="🔙 Back / Назад", callback_data="nav:main_menu"),
            ],
        ]
    )
    return keyboard


def get_help_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    """Get help screen keyboard.

    Args:
        lang: Language code ('ru' or 'en')

    Returns:
        InlineKeyboardMarkup with help screen buttons
    """
    texts = {
        "ru": {
            "events": "🎭 К мероприятиям",
            "back": "🔙 В меню",
        },
        "en": {
            "events": "🎭 Browse Events",
            "back": "🔙 Main Menu",
        },
    }

    t = texts.get(lang, texts["en"])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t["events"], callback_data="menu:events"),
            ],
            [
                InlineKeyboardButton(text=t["back"], callback_data="nav:main_menu"),
            ],
        ]
    )
    return keyboard


def get_tickets_keyboard(lang: str = "en", has_tickets: bool = False) -> InlineKeyboardMarkup:
    """Get tickets screen keyboard.

    Args:
        lang: Language code ('ru' or 'en')
        has_tickets: Whether user has tickets

    Returns:
        InlineKeyboardMarkup with tickets screen buttons
    """
    texts = {
        "ru": {
            "events": "🎭 Купить билеты",
            "back": "🔙 В меню",
        },
        "en": {
            "events": "🎭 Buy Tickets",
            "back": "🔙 Main Menu",
        },
    }

    t = texts.get(lang, texts["en"])

    buttons = [
        [InlineKeyboardButton(text=t["events"], callback_data="menu:events")],
        [InlineKeyboardButton(text=t["back"], callback_data="nav:main_menu")],
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_back_button(lang: str = "en", callback_data: str = "nav:main_menu") -> InlineKeyboardMarkup:
    """Get single back button keyboard.

    Args:
        lang: Language code ('ru' or 'en')
        callback_data: Callback data for back button

    Returns:
        InlineKeyboardMarkup with back button
    """
    texts = {
        "ru": "🔙 Назад",
        "en": "🔙 Back",
    }

    text = texts.get(lang, texts["en"])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=callback_data)],
        ]
    )
    return keyboard


def get_confirmation_keyboard(lang: str = "en", action: str = "confirm") -> InlineKeyboardMarkup:
    """Get confirmation dialog keyboard.

    Args:
        lang: Language code ('ru' or 'en')
        action: Action identifier for callback

    Returns:
        InlineKeyboardMarkup with confirm/cancel buttons
    """
    texts = {
        "ru": {
            "confirm": "✅ Подтвердить",
            "cancel": "❌ Отмена",
        },
        "en": {
            "confirm": "✅ Confirm",
            "cancel": "❌ Cancel",
        },
    }

    t = texts.get(lang, texts["en"])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t["confirm"], callback_data=f"confirm:{action}"),
                InlineKeyboardButton(text=t["cancel"], callback_data="cancel"),
            ],
        ]
    )
    return keyboard


def get_event_list_keyboard(
    events: list[dict],
    lang: str = "en",
    page: int = 0,
    page_size: int = 5,
) -> InlineKeyboardMarkup:
    """Get event list keyboard with pagination.

    Args:
        events: List of event dictionaries with 'id' and 'name' keys
        lang: Language code ('ru' or 'en')
        page: Current page number (0-indexed)
        page_size: Number of events per page

    Returns:
        InlineKeyboardMarkup with event buttons and pagination
    """
    texts = {
        "ru": {
            "prev_page": "⬅️ Пред.",
            "next_page": "След. ➡️",
            "back": "🔙 В меню",
        },
        "en": {
            "prev_page": "⬅️ Prev",
            "next_page": "Next ➡️",
            "back": "🔙 Main Menu",
        },
    }

    t = texts.get(lang, texts["en"])

    # Calculate pagination
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_events = events[start_idx:end_idx]
    total_pages = (len(events) + page_size - 1) // page_size

    # Event buttons
    buttons = []
    for event in page_events:
        buttons.append([
            InlineKeyboardButton(
                text=f"🎭 {event.get('name', 'Event')[:40]}",
                callback_data=f"event:view:{event.get('id', 0)}"
            )
        ])

    # Pagination row
    if total_pages > 1:
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(
                InlineKeyboardButton(text=t["prev_page"], callback_data=f"list:page:{page - 1}")
            )
        pagination_buttons.append(
            InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop")
        )
        if page < total_pages - 1:
            pagination_buttons.append(
                InlineKeyboardButton(text=t["next_page"], callback_data=f"list:page:{page + 1}")
            )
        buttons.append(pagination_buttons)

    # Back button
    buttons.append([InlineKeyboardButton(text=t["back"], callback_data="nav:main_menu")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
