"""
Bot Message Handlers

Handlers for Telegram bot commands and callbacks.
Uses inline keyboard buttons (system buttons) for navigation.
"""

from aiogram import Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    get_main_menu_keyboard,
    get_events_navigation_keyboard,
    get_language_keyboard,
    get_help_keyboard,
    get_tickets_keyboard,
)


router = Router()


def get_user_lang(message_or_callback) -> str:
    """Get user's language preference.

    Args:
        message_or_callback: Message or CallbackQuery object

    Returns:
        Language code ('ru' or 'en')
    """
    # Try to get from Telegram user settings
    user = None
    if hasattr(message_or_callback, 'from_user'):
        user = message_or_callback.from_user
    elif hasattr(message_or_callback, 'message') and message_or_callback.message:
        user = message_or_callback.from_user

    if user and user.language_code:
        if user.language_code.startswith('ru'):
            return 'ru'
    return 'en'


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message):
    """Handle /start command with agent deep link.

    Agent identification uses Agent ID (internal primary key),
    NOT fid or token. Format: ?start=agent_{agent_id}
    """
    lang = get_user_lang(message)

    # Extract agent ID from deep link parameter
    # Format: ?start=agent_{agent_id} (uses internal agent.id, NOT fid/token)
    args = message.text.split(maxsplit=1)
    deep_link = args[1] if len(args) > 1 else None

    if deep_link and deep_link.startswith("agent_"):
        try:
            agent_id = int(deep_link.replace("agent_", ""))
            # TODO: Lookup agent by id (not fid) and link user

            welcome_text = {
                'ru': (
                    f"🎉 Добро пожаловать!\n\n"
                    f"Вы подключены к агенту ID {agent_id}.\n"
                    f"Выберите действие:"
                ),
                'en': (
                    f"🎉 Welcome!\n\n"
                    f"You are connected to agent ID {agent_id}.\n"
                    f"Choose an action:"
                ),
            }

            await message.answer(
                welcome_text.get(lang, welcome_text['en']),
                reply_markup=get_main_menu_keyboard(lang)
            )
        except ValueError:
            error_text = {
                'ru': "❌ Неверная ссылка агента. Используйте корректную ссылку.",
                'en': "❌ Invalid agent link. Please use a valid link.",
            }
            await message.answer(error_text.get(lang, error_text['en']))
    else:
        no_agent_text = {
            'ru': (
                "👋 Добро пожаловать в TG-Ticket-Agent!\n\n"
                "Используйте ссылку агента для начала работы с ботом."
            ),
            'en': (
                "👋 Welcome to TG-Ticket-Agent!\n\n"
                "Please use an agent link to start browsing events."
            ),
        }
        await message.answer(no_agent_text.get(lang, no_agent_text['en']))


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command without deep link."""
    lang = get_user_lang(message)

    welcome_text = {
        'ru': (
            "🎭 <b>TG-Ticket-Agent</b>\n\n"
            "Этот бот позволяет покупать билеты на мероприятия.\n\n"
            "Для начала работы перейдите по ссылке агента,\n"
            "или выберите действие из меню ниже:"
        ),
        'en': (
            "🎭 <b>TG-Ticket-Agent</b>\n\n"
            "This bot allows you to purchase event tickets.\n\n"
            "To get started, use an agent link,\n"
            "or choose an action from the menu below:"
        ),
    }

    await message.answer(
        welcome_text.get(lang, welcome_text['en']),
        reply_markup=get_main_menu_keyboard(lang)
    )


@router.message(Command("events"))
async def cmd_events(message: Message):
    """Handle /events command."""
    lang = get_user_lang(message)

    loading_text = {
        'ru': "⏳ Загрузка мероприятий...\n\n(Функция в разработке)",
        'en': "⏳ Loading events...\n\n(Feature in development)",
    }

    # TODO: Fetch and display events for user's agent
    await message.answer(
        loading_text.get(lang, loading_text['en']),
        reply_markup=get_events_navigation_keyboard(lang, has_prev=False, has_next=True)
    )


@router.message(Command("mytickets"))
async def cmd_my_tickets(message: Message):
    """Handle /mytickets command."""
    lang = get_user_lang(message)

    no_tickets_text = {
        'ru': (
            "🎫 <b>Мои билеты</b>\n\n"
            "У вас пока нет билетов.\n"
            "Перейдите в раздел мероприятий, чтобы купить билеты!"
        ),
        'en': (
            "🎫 <b>My Tickets</b>\n\n"
            "You don't have any tickets yet.\n"
            "Go to events section to buy tickets!"
        ),
    }

    # TODO: Fetch and display user's tickets
    await message.answer(
        no_tickets_text.get(lang, no_tickets_text['en']),
        reply_markup=get_tickets_keyboard(lang, has_tickets=False)
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    lang = get_user_lang(message)

    help_text = {
        'ru': (
            "❓ <b>Помощь</b>\n\n"
            "Этот бот позволяет покупать билеты на мероприятия.\n\n"
            "<b>Как пользоваться:</b>\n"
            "1️⃣ Перейдите по ссылке агента\n"
            "2️⃣ Просмотрите доступные мероприятия\n"
            "3️⃣ Выберите места и оплатите\n"
            "4️⃣ Получите билеты в этом чате!\n\n"
            "<b>Команды:</b>\n"
            "/start - Запустить бота\n"
            "/events - Просмотр мероприятий\n"
            "/mytickets - Мои билеты\n"
            "/help - Справка\n"
            "/language - Сменить язык"
        ),
        'en': (
            "❓ <b>Help</b>\n\n"
            "This bot allows you to purchase event tickets.\n\n"
            "<b>How to use:</b>\n"
            "1️⃣ Click an agent link to connect\n"
            "2️⃣ Browse available events\n"
            "3️⃣ Select seats and purchase\n"
            "4️⃣ Receive your tickets here!\n\n"
            "<b>Commands:</b>\n"
            "/start - Start the bot\n"
            "/events - Browse events\n"
            "/mytickets - View your tickets\n"
            "/help - This message\n"
            "/language - Change language"
        ),
    }

    await message.answer(
        help_text.get(lang, help_text['en']),
        reply_markup=get_help_keyboard(lang)
    )


@router.message(Command("language"))
async def cmd_language(message: Message):
    """Handle /language command."""
    lang = get_user_lang(message)

    select_text = {
        'ru': "🌐 Выберите язык / Select language:",
        'en': "🌐 Select language / Выберите язык:",
    }

    await message.answer(
        select_text.get(lang, select_text['en']),
        reply_markup=get_language_keyboard()
    )


# ============================================================================
# MENU CALLBACK HANDLERS
# ============================================================================

@router.callback_query(F.data == "menu:events")
async def callback_menu_events(callback: CallbackQuery):
    """Handle events menu button."""
    lang = get_user_lang(callback)

    loading_text = {
        'ru': "⏳ Загрузка мероприятий...\n\n(Функция в разработке)",
        'en': "⏳ Loading events...\n\n(Feature in development)",
    }

    await callback.message.edit_text(
        loading_text.get(lang, loading_text['en']),
        reply_markup=get_events_navigation_keyboard(lang, has_prev=False, has_next=True)
    )
    await callback.answer()


@router.callback_query(F.data == "menu:mytickets")
async def callback_menu_mytickets(callback: CallbackQuery):
    """Handle my tickets menu button."""
    lang = get_user_lang(callback)

    no_tickets_text = {
        'ru': (
            "🎫 <b>Мои билеты</b>\n\n"
            "У вас пока нет билетов.\n"
            "Перейдите в раздел мероприятий, чтобы купить билеты!"
        ),
        'en': (
            "🎫 <b>My Tickets</b>\n\n"
            "You don't have any tickets yet.\n"
            "Go to events section to buy tickets!"
        ),
    }

    await callback.message.edit_text(
        no_tickets_text.get(lang, no_tickets_text['en']),
        reply_markup=get_tickets_keyboard(lang, has_tickets=False)
    )
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def callback_menu_help(callback: CallbackQuery):
    """Handle help menu button."""
    lang = get_user_lang(callback)

    help_text = {
        'ru': (
            "❓ <b>Помощь</b>\n\n"
            "Этот бот позволяет покупать билеты на мероприятия.\n\n"
            "<b>Как пользоваться:</b>\n"
            "1️⃣ Перейдите по ссылке агента\n"
            "2️⃣ Просмотрите доступные мероприятия\n"
            "3️⃣ Выберите места и оплатите\n"
            "4️⃣ Получите билеты в этом чате!\n\n"
            "<b>Команды:</b>\n"
            "/start - Запустить бота\n"
            "/events - Просмотр мероприятий\n"
            "/mytickets - Мои билеты\n"
            "/help - Справка\n"
            "/language - Сменить язык"
        ),
        'en': (
            "❓ <b>Help</b>\n\n"
            "This bot allows you to purchase event tickets.\n\n"
            "<b>How to use:</b>\n"
            "1️⃣ Click an agent link to connect\n"
            "2️⃣ Browse available events\n"
            "3️⃣ Select seats and purchase\n"
            "4️⃣ Receive your tickets here!\n\n"
            "<b>Commands:</b>\n"
            "/start - Start the bot\n"
            "/events - Browse events\n"
            "/mytickets - View your tickets\n"
            "/help - This message\n"
            "/language - Change language"
        ),
    }

    await callback.message.edit_text(
        help_text.get(lang, help_text['en']),
        reply_markup=get_help_keyboard(lang)
    )
    await callback.answer()


@router.callback_query(F.data == "menu:language")
async def callback_menu_language(callback: CallbackQuery):
    """Handle language menu button."""
    lang = get_user_lang(callback)

    select_text = {
        'ru': "🌐 Выберите язык / Select language:",
        'en': "🌐 Select language / Выберите язык:",
    }

    await callback.message.edit_text(
        select_text.get(lang, select_text['en']),
        reply_markup=get_language_keyboard()
    )
    await callback.answer()


# ============================================================================
# NAVIGATION CALLBACK HANDLERS
# ============================================================================

@router.callback_query(F.data == "nav:main_menu")
async def callback_nav_main_menu(callback: CallbackQuery):
    """Handle back to main menu navigation."""
    lang = get_user_lang(callback)

    menu_text = {
        'ru': "🎭 <b>Главное меню</b>\n\nВыберите действие:",
        'en': "🎭 <b>Main Menu</b>\n\nChoose an action:",
    }

    await callback.message.edit_text(
        menu_text.get(lang, menu_text['en']),
        reply_markup=get_main_menu_keyboard(lang)
    )
    await callback.answer()


@router.callback_query(F.data == "nav:next_event")
async def callback_nav_next_event(callback: CallbackQuery):
    """Handle next event navigation."""
    # TODO: Show next event
    await callback.answer("Next event (not implemented)")


@router.callback_query(F.data == "nav:prev_event")
async def callback_nav_prev_event(callback: CallbackQuery):
    """Handle previous event navigation."""
    # TODO: Show previous event
    await callback.answer("Previous event (not implemented)")


@router.callback_query(F.data == "nav:event_list")
async def callback_nav_event_list(callback: CallbackQuery):
    """Handle event list navigation."""
    # TODO: Show event list
    await callback.answer("Event list (not implemented)")


# ============================================================================
# LANGUAGE CALLBACK HANDLERS
# ============================================================================

@router.callback_query(F.data.startswith("lang:"))
async def callback_language_select(callback: CallbackQuery):
    """Handle language selection."""
    selected_lang = callback.data.replace("lang:", "")

    # TODO: Save language preference to database

    success_text = {
        'ru': "✅ Язык изменён на русский",
        'en': "✅ Language changed to English",
    }

    menu_text = {
        'ru': "🎭 <b>Главное меню</b>\n\nВыберите действие:",
        'en': "🎭 <b>Main Menu</b>\n\nChoose an action:",
    }

    await callback.answer(success_text.get(selected_lang, success_text['en']))
    await callback.message.edit_text(
        menu_text.get(selected_lang, menu_text['en']),
        reply_markup=get_main_menu_keyboard(selected_lang)
    )


# ============================================================================
# EVENT CALLBACK HANDLERS
# ============================================================================

@router.callback_query(F.data.startswith("event:"))
async def callback_event(callback: CallbackQuery):
    """Handle event-related callbacks."""
    parts = callback.data.split(":")
    action = parts[1] if len(parts) > 1 else None
    event_id = parts[2] if len(parts) > 2 else None

    if action == "view":
        # TODO: Show event details
        await callback.answer(f"Viewing event {event_id}")
    elif action == "buy":
        # TODO: Open ticket purchase flow
        await callback.answer(f"Buying tickets for event {event_id}")
    else:
        await callback.answer("Unknown action")


# ============================================================================
# MISC CALLBACK HANDLERS
# ============================================================================

@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    """Handle no-op callback (for display-only buttons)."""
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery):
    """Handle cancel action."""
    lang = get_user_lang(callback)

    menu_text = {
        'ru': "🎭 <b>Главное меню</b>\n\nВыберите действие:",
        'en': "🎭 <b>Main Menu</b>\n\nChoose an action:",
    }

    await callback.message.edit_text(
        menu_text.get(lang, menu_text['en']),
        reply_markup=get_main_menu_keyboard(lang)
    )
    await callback.answer()


def register_handlers(dp: Dispatcher):
    """Register all handlers with dispatcher."""
    dp.include_router(router)
