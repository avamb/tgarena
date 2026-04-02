"""
Telegram Bot Handlers Module

Contains all message and callback handlers for the bot.
"""

import logging
import math
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    WebAppInfo, URLInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

try:
    from app.bot.localization import get_text, get_user_language, get_age_restriction_text
    from app.core.database import get_async_session
    from app.models import Agent, User
    from app.services.bill24 import Bill24Client, Bill24Error
except ModuleNotFoundError:
    from backend.app.bot.localization import get_text, get_user_language, get_age_restriction_text
    from backend.app.core.database import get_async_session
    from backend.app.models import Agent, User
    from backend.app.services.bill24 import Bill24Client, Bill24Error

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Events per page for pagination
EVENTS_PER_PAGE = 5

# Create router for handlers
router = Router(name="main")


async def get_or_create_user(session: AsyncSession, message: Message) -> User:
    """Get existing user or create new one from Telegram message."""
    telegram_user = message.from_user

    # Try to find existing user
    result = await session.execute(
        select(User).where(User.telegram_chat_id == telegram_user.id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Create new user
        user = User(
            telegram_chat_id=telegram_user.id,
            telegram_username=telegram_user.username,
            telegram_first_name=telegram_user.first_name,
            telegram_last_name=telegram_user.last_name,
            telegram_language_code=telegram_user.language_code,
            preferred_language=get_user_language(telegram_user.language_code),
            last_active_at=datetime.utcnow(),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Created new user: chat_id={telegram_user.id}, username={telegram_user.username}")
    else:
        # Update last_active_at for existing user
        user.last_active_at = datetime.utcnow()
        await session.commit()

    return user


async def get_agent_by_fid(session: AsyncSession, fid: int) -> Optional[Agent]:
    """Get agent by Bill24 FID."""
    result = await session.execute(
        select(Agent).where(Agent.fid == fid, Agent.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_agent_by_id(session: AsyncSession, agent_id: int) -> Optional[Agent]:
    """Get agent by database ID (used for deep links)."""
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    return result.scalar_one_or_none()


def parse_deep_link(text: str) -> Optional[int]:
    """
    Parse agent ID from deep link parameter.

    Expected format: agent_12345 where 12345 is the agent database ID.
    Note: Deep links use agent.id (NOT Bill24 FID) for identification.

    Args:
        text: Deep link parameter text

    Returns:
        Agent ID or None if not valid
    """
    if not text:
        return None

    # Match pattern: agent_<id>
    match = re.match(r'^agent_(\d+)$', text.strip())
    if match:
        return int(match.group(1))

    return None


def get_main_keyboard(lang: str = "ru", has_agent: bool = False) -> InlineKeyboardMarkup:
    """Get main menu keyboard."""
    builder = InlineKeyboardBuilder()

    if has_agent:
        builder.row(
            InlineKeyboardButton(
                text=get_text("btn_view_events", lang),
                callback_data="view_events"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_my_tickets", lang),
            callback_data="my_tickets"
        ),
        InlineKeyboardButton(
            text=get_text("btn_help", lang),
            callback_data="help"
        )
    )

    return builder.as_markup()


async def fetch_events_from_bill24(agent: Agent) -> List[Dict[str, Any]]:
    """
    Fetch events from Bill24 API for a given agent.

    Uses Redis caching when ENABLE_EVENT_CACHING is true to avoid
    hitting the API on every request. Cache key: agent_{agent.id}.

    Args:
        agent: Agent model with Bill24 credentials

    Returns:
        List of event dictionaries
    """
    try:
        from app.core.config import settings as app_settings
        from app.core.redis_client import event_cache
    except ModuleNotFoundError:
        from backend.app.core.config import settings as app_settings
        from backend.app.core.redis_client import event_cache

    # Check cache first (if caching is enabled)
    if app_settings.ENABLE_EVENT_CACHING:
        cache_key = f"agent_{agent.id}"
        cached_events = await event_cache.get(cache_key)
        if cached_events is not None:
            logger.info(f"Events cache HIT for agent {agent.id} (fid={agent.fid}): {len(cached_events)} events")
            return cached_events

    client = Bill24Client(
        fid=agent.fid,
        token=agent.token,
        zone=agent.zone or "test"
    )

    try:
        response = await client.get_all_actions()
        events = response.get("actionList", [])

        logger.info(
            f"Fetched {len(events)} events from Bill24 for agent {agent.id} "
            f"(fid={agent.fid}, zone={agent.zone})"
        )

        # Sort events by firstEventDate (format: dd.MM.yyyy)
        # Parse to comparable format for proper date sorting
        def sort_key(event):
            date_str = event.get("firstEventDate", "")
            try:
                # Convert dd.MM.yyyy to yyyy.MM.dd for string comparison
                parts = date_str.split(".")
                if len(parts) == 3:
                    return f"{parts[2]}.{parts[1]}.{parts[0]}"
            except (ValueError, IndexError):
                pass
            return ""

        events.sort(key=sort_key)

        # Store in cache if caching is enabled
        if app_settings.ENABLE_EVENT_CACHING:
            cache_key = f"agent_{agent.id}"
            await event_cache.set(cache_key, events, ttl=app_settings.EVENT_CACHE_TTL)
            logger.info(f"Events cached for agent {agent.id} (TTL={app_settings.EVENT_CACHE_TTL}s)")

        return events
    except Bill24Error as e:
        logger.error(f"Bill24 API error fetching events for agent {agent.id} (fid={agent.fid}): {e}")
        raise
    finally:
        await client.close()


def format_event_date(date_str: str) -> str:
    """
    Format event date for display.

    Bill24 API returns dates in multiple formats:
    - firstEventDate/lastEventDate: "dd.MM.yyyy" (e.g., "01.11.2026")
    - sellEndTime: ISO-8601 (e.g., "2026-11-01T18:00:00Z")
    - actionEventList[].day: "dd.MM.yyyy"
    - actionEventList[].time: "HH:mm"
    """
    if not date_str:
        return "TBD"

    # Already in dd.MM.yyyy format from Bill24 — return as-is
    if len(date_str) == 10 and date_str[2] == "." and date_str[5] == ".":
        return date_str

    try:
        # Try ISO format (for sellEndTime and similar fields)
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, AttributeError):
        return date_str


def calculate_countdown(event_date_str: str, lang: str = "ru") -> str:
    """
    Calculate countdown to event start.

    Args:
        event_date_str: ISO format event date string
        lang: Language code for text formatting

    Returns:
        Human-readable countdown string (e.g., "2 дня 5 часов")
        or empty string if event already started or date invalid
    """
    if not event_date_str:
        return ""

    try:
        # Parse event date - handle both dd.MM.yyyy and ISO formats
        if len(event_date_str) == 10 and event_date_str[2] == "." and event_date_str[5] == ".":
            # Bill24 format: dd.MM.yyyy
            event_dt = datetime.strptime(event_date_str, "%d.%m.%Y").replace(tzinfo=timezone.utc)
        else:
            # ISO format
            event_dt = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))

        # Make sure we have a timezone-aware datetime for comparison
        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        delta = event_dt - now

        # Event already started or passed
        if delta.total_seconds() <= 0:
            return get_text("countdown_started", lang)

        total_seconds = int(delta.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        # Build countdown parts
        parts = []

        if days > 0:
            parts.append(get_text("countdown_days", lang, count=days))

        if hours > 0 or days > 0:
            parts.append(get_text("countdown_hours", lang, count=hours))

        # Only show minutes if less than 1 day
        if days == 0 and minutes > 0:
            parts.append(get_text("countdown_minutes", lang, count=minutes))

        if not parts:
            return get_text("countdown_starting_soon", lang)

        return " ".join(parts)

    except (ValueError, AttributeError, TypeError):
        return ""


def build_events_list_message(
    events: List[Dict[str, Any]],
    page: int,
    total_pages: int,
    lang: str
) -> str:
    """Build formatted message with event list."""
    if not events:
        return get_text("no_events", lang)

    message_parts = [get_text("events_list_title", lang, page=page, total_pages=total_pages)]
    message_parts.append("")  # Empty line

    for i, event in enumerate(events, start=1):
        event_name = event.get("fullActionName", event.get("actionName", "Unknown"))
        event_date = format_event_date(event.get("firstEventDate", ""))
        min_price = event.get("minPrice", 0)

        # Calculate global event number on this page
        global_number = (page - 1) * EVENTS_PER_PAGE + i

        event_line = get_text(
            "event_list_item",
            lang,
            number=global_number,
            name=event_name[:50] + ("..." if len(event_name) > 50 else ""),
            date=event_date,
            min_price=min_price
        )
        message_parts.append(event_line)
        message_parts.append("")  # Empty line between events

    return "\n".join(message_parts)


def build_events_pagination_keyboard(
    events: List[Dict[str, Any]],
    page: int,
    total_pages: int,
    lang: str
) -> InlineKeyboardMarkup:
    """Build keyboard with event selection and pagination."""
    builder = InlineKeyboardBuilder()

    # Add buttons for each event on current page
    for i, event in enumerate(events):
        event_id = event.get("actionId", i)
        event_name = event.get("fullActionName", event.get("actionName", "Event"))

        # Truncate name for button
        button_name = event_name[:25] + ("..." if len(event_name) > 25 else "")

        builder.row(
            InlineKeyboardButton(
                text=f"🎫 {button_name}",
                callback_data=f"event_{event_id}"
            )
        )

    # Add pagination buttons
    pagination_buttons = []

    if page > 1:
        pagination_buttons.append(
            InlineKeyboardButton(
                text=get_text("btn_page_prev", lang),
                callback_data=f"events_page_{page - 1}"
            )
        )

    # Page indicator
    pagination_buttons.append(
        InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="noop"  # No action, just display
        )
    )

    if page < total_pages:
        pagination_buttons.append(
            InlineKeyboardButton(
                text=get_text("btn_page_next", lang),
                callback_data=f"events_page_{page + 1}"
            )
        )

    if pagination_buttons:
        builder.row(*pagination_buttons)

    # Back button
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="back_to_main"
        )
    )

    return builder.as_markup()


def get_page_events(events: List[Dict[str, Any]], page: int) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get events for a specific page.

    Returns:
        Tuple of (events_on_page, total_pages)
    """
    total_pages = max(1, math.ceil(len(events) / EVENTS_PER_PAGE))
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * EVENTS_PER_PAGE
    end_idx = start_idx + EVENTS_PER_PAGE

    return events[start_idx:end_idx], total_pages


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Handle /start command with optional deep link.

    Deep link format: t.me/BotUsername?start=agent_12345

    When user comes via agent deep link, automatically loads events using get_all_actions.
    If API doesn't return events, displays a message that no events are found.
    """
    telegram_user = message.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    # Parse deep link parameter
    args = message.text.split(maxsplit=1)
    deep_link_param = args[1] if len(args) > 1 else None

    # Handle paid_ deep link (return from payment)
    if deep_link_param and deep_link_param.startswith("paid_"):
        try:
            from app.bot.purchase_handlers import handle_paid_return
        except ModuleNotFoundError:
            from backend.app.bot.purchase_handlers import handle_paid_return
        await handle_paid_return(message, deep_link_param)
        return

    agent_id = parse_deep_link(deep_link_param) if deep_link_param else None

    async for session in get_async_session():
        # Get or create user
        user = await get_or_create_user(session, message)
        lang = user.preferred_language or lang

        agent = None
        if agent_id:
            # Try to find agent by ID (from deep link)
            agent = await get_agent_by_id(session, agent_id)

            if agent is None:
                await message.answer(
                    get_text("error_agent_not_found", lang),
                    reply_markup=get_main_keyboard(lang, has_agent=False)
                )
                return

            if not agent.is_active:
                await message.answer(
                    get_text("error_agent_inactive", lang),
                    reply_markup=get_main_keyboard(lang, has_agent=False)
                )
                return

            # Update user's current agent
            user.current_agent_id = agent.id
            await session.commit()

            # Send welcome message with agent
            await message.answer(
                get_text("welcome_with_agent", lang, agent_name=agent.name),
                parse_mode="HTML"
            )

            # Automatically load events using get_all_actions
            loading_msg = await message.answer(get_text("loading_events", lang))

            try:
                # Fetch events from Bill24 using get_all_actions
                events = await fetch_events_from_bill24(agent)

                if not events:
                    # No events found - display message
                    await loading_msg.edit_text(
                        get_text("no_events", lang),
                        reply_markup=get_main_keyboard(lang, has_agent=True)
                    )
                    return

                # Get first page of events
                page_events, total_pages = get_page_events(events, page=1)

                # Build message and keyboard
                message_text = build_events_list_message(page_events, page=1, total_pages=total_pages, lang=lang)
                keyboard = build_events_pagination_keyboard(page_events, page=1, total_pages=total_pages, lang=lang)

                await loading_msg.edit_text(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )

            except Bill24Error as e:
                logger.error(f"Failed to fetch events on /start: {e}")
                await loading_msg.edit_text(
                    get_text("error_fetching_events", lang),
                    reply_markup=get_main_keyboard(lang, has_agent=True)
                )
            except Exception as e:
                logger.exception(f"Unexpected error fetching events on /start: {e}")
                await loading_msg.edit_text(
                    get_text("error_general", lang),
                    reply_markup=get_main_keyboard(lang, has_agent=True)
                )
        else:
            # No agent in deep link - check if user has a current agent
            if user.current_agent_id is not None:
                # Get agent for the user
                result = await session.execute(
                    select(Agent).where(Agent.id == user.current_agent_id)
                )
                agent = result.scalar_one_or_none()

                if agent and agent.is_active:
                    # Send welcome and load events
                    await message.answer(
                        get_text("welcome_with_agent", lang, agent_name=agent.name),
                        parse_mode="HTML"
                    )

                    # Automatically load events
                    loading_msg = await message.answer(get_text("loading_events", lang))

                    try:
                        events = await fetch_events_from_bill24(agent)

                        if not events:
                            await loading_msg.edit_text(
                                get_text("no_events", lang),
                                reply_markup=get_main_keyboard(lang, has_agent=True)
                            )
                            return

                        page_events, total_pages = get_page_events(events, page=1)
                        message_text = build_events_list_message(page_events, page=1, total_pages=total_pages, lang=lang)
                        keyboard = build_events_pagination_keyboard(page_events, page=1, total_pages=total_pages, lang=lang)

                        await loading_msg.edit_text(
                            message_text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )

                    except Bill24Error as e:
                        logger.error(f"Failed to fetch events on /start (existing agent): {e}")
                        await loading_msg.edit_text(
                            get_text("error_fetching_events", lang),
                            reply_markup=get_main_keyboard(lang, has_agent=True)
                        )
                    except Exception as e:
                        logger.exception(f"Unexpected error fetching events on /start: {e}")
                        await loading_msg.edit_text(
                            get_text("error_general", lang),
                            reply_markup=get_main_keyboard(lang, has_agent=True)
                        )
                else:
                    # Agent no longer valid
                    await message.answer(
                        get_text("welcome", lang),
                        reply_markup=get_main_keyboard(lang, has_agent=False)
                    )
            else:
                # Send general welcome message (no agent)
                await message.answer(
                    get_text("welcome", lang),
                    reply_markup=get_main_keyboard(lang, has_agent=False)
                )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    telegram_user = message.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    async for session in get_async_session():
        user = await get_or_create_user(session, message)
        lang = user.preferred_language or lang

    await message.answer(get_text("help_text", lang))


@router.message(Command("tickets"))
async def cmd_tickets(message: Message):
    """Handle /tickets command - show user's tickets."""
    telegram_user = message.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    async for session in get_async_session():
        user = await get_or_create_user(session, message)
        lang = user.preferred_language or lang

        # TODO: Implement ticket listing from Bill24
        await message.answer(get_text("no_tickets", lang))


@router.message(Command("events"))
async def cmd_events(message: Message):
    """Handle /events command - show events for user's current agent."""
    telegram_user = message.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    async for session in get_async_session():
        user = await get_or_create_user(session, message)
        lang = user.preferred_language or lang

        if not user.current_agent_id:
            await message.answer(get_text("error_no_agent", lang))
            return

        # Get agent
        result = await session.execute(
            select(Agent).where(Agent.id == user.current_agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            await message.answer(get_text("error_no_agent", lang))
            return

        if not agent.is_active:
            await message.answer(get_text("error_agent_inactive", lang))
            return

        # Show loading message
        loading_msg = await message.answer(get_text("loading_events", lang))

        try:
            events = await fetch_events_from_bill24(agent)

            if not events:
                await loading_msg.edit_text(get_text("no_events", lang))
                return

            page_events, total_pages = get_page_events(events, page=1)
            message_text = build_events_list_message(page_events, page=1, total_pages=total_pages, lang=lang)
            keyboard = build_events_pagination_keyboard(page_events, page=1, total_pages=total_pages, lang=lang)

            await loading_msg.edit_text(
                message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

        except Bill24Error as e:
            logger.error(f"Failed to fetch events via /events command: {e}")
            await loading_msg.edit_text(get_text("error_fetching_events", lang))
        except Exception as e:
            logger.exception(f"Unexpected error in /events command: {e}")
            await loading_msg.edit_text(get_text("error_general", lang))


@router.message(Command("mytickets"))
async def cmd_mytickets(message: Message):
    """Handle /mytickets command - alias for /tickets."""
    telegram_user = message.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    async for session in get_async_session():
        user = await get_or_create_user(session, message)
        lang = user.preferred_language or lang

        await message.answer(get_text("no_tickets", lang))


@router.message(Command("language"))
async def cmd_language(message: Message):
    """Handle /language command - show language selection."""
    telegram_user = message.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en"),
    )

    await message.answer(
        get_text("select_language", lang),
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("set_lang_"))
async def callback_set_language(callback: CallbackQuery):
    """Handle language selection callback."""
    telegram_user = callback.from_user
    selected_lang = callback.data.replace("set_lang_", "")

    if selected_lang not in ("ru", "en"):
        selected_lang = "ru"

    await callback.answer()

    async for session in get_async_session():
        result = await session.execute(
            select(User).where(User.telegram_chat_id == telegram_user.id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.preferred_language = selected_lang
            await session.commit()

    success_text = {
        "ru": "✅ Язык изменён на русский",
        "en": "✅ Language changed to English",
    }

    await callback.message.edit_text(
        success_text.get(selected_lang, success_text["en"]),
        reply_markup=get_main_keyboard(selected_lang, has_agent=True)
    )


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Handle help button callback."""
    telegram_user = callback.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    await callback.answer()
    await callback.message.answer(get_text("help_text", lang))


@router.callback_query(F.data == "my_tickets")
async def callback_my_tickets(callback: CallbackQuery):
    """Handle my tickets button callback."""
    telegram_user = callback.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    await callback.answer()
    # TODO: Implement ticket listing
    await callback.message.answer(get_text("no_tickets", lang))


@router.callback_query(F.data == "view_events")
async def callback_view_events(callback: CallbackQuery):
    """Handle view events button callback - shows first page of events."""
    telegram_user = callback.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    await callback.answer()

    async for session in get_async_session():
        # Get user and their current agent
        result = await session.execute(
            select(User).where(User.telegram_chat_id == telegram_user.id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.current_agent_id:
            await callback.message.answer(get_text("error_no_agent", lang))
            return

        lang = user.preferred_language or lang

        # Get agent
        result = await session.execute(
            select(Agent).where(Agent.id == user.current_agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            await callback.message.answer(get_text("error_no_agent", lang))
            return

        # Check if agent is active
        if not agent.is_active:
            await callback.message.answer(get_text("error_agent_inactive", lang))
            return

        # Show loading message
        loading_msg = await callback.message.answer(get_text("loading_events", lang))

        try:
            # Fetch events from Bill24
            events = await fetch_events_from_bill24(agent)

            if not events:
                await loading_msg.edit_text(get_text("no_events", lang))
                return

            # Get first page
            page_events, total_pages = get_page_events(events, page=1)

            # Build message and keyboard
            message_text = build_events_list_message(page_events, page=1, total_pages=total_pages, lang=lang)
            keyboard = build_events_pagination_keyboard(page_events, page=1, total_pages=total_pages, lang=lang)

            await loading_msg.edit_text(
                message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

        except Bill24Error as e:
            logger.error(f"Failed to fetch events: {e}")
            await loading_msg.edit_text(get_text("error_fetching_events", lang))
        except Exception as e:
            logger.exception(f"Unexpected error fetching events: {e}")
            await loading_msg.edit_text(get_text("error_general", lang))


@router.callback_query(F.data.startswith("events_page_"))
async def callback_events_page(callback: CallbackQuery):
    """Handle pagination button callbacks."""
    telegram_user = callback.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    # Extract page number from callback data
    try:
        page = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        page = 1

    await callback.answer()

    async for session in get_async_session():
        # Get user and their current agent
        result = await session.execute(
            select(User).where(User.telegram_chat_id == telegram_user.id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.current_agent_id:
            await callback.message.edit_text(get_text("error_no_agent", lang))
            return

        lang = user.preferred_language or lang

        # Get agent
        result = await session.execute(
            select(Agent).where(Agent.id == user.current_agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            await callback.message.edit_text(get_text("error_no_agent", lang))
            return

        # Check if agent is active
        if not agent.is_active:
            await callback.message.edit_text(get_text("error_agent_inactive", lang))
            return

        try:
            # Fetch events from Bill24
            events = await fetch_events_from_bill24(agent)

            if not events:
                await callback.message.edit_text(get_text("no_events", lang))
                return

            # Get requested page
            page_events, total_pages = get_page_events(events, page=page)

            # Build message and keyboard
            message_text = build_events_list_message(page_events, page=page, total_pages=total_pages, lang=lang)
            keyboard = build_events_pagination_keyboard(page_events, page=page, total_pages=total_pages, lang=lang)

            await callback.message.edit_text(
                message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

        except Bill24Error as e:
            logger.error(f"Failed to fetch events: {e}")
            await callback.message.edit_text(get_text("error_fetching_events", lang))
        except Exception as e:
            logger.exception(f"Unexpected error fetching events: {e}")
            await callback.message.edit_text(get_text("error_general", lang))


def build_event_details_message(event: Dict[str, Any], lang: str) -> str:
    """Build formatted message for event details."""
    event_name = event.get("fullActionName", event.get("actionName", "Unknown"))
    event_date_str = event.get("firstEventDate", "")
    event_date = format_event_date(event_date_str)
    venue = event.get("venueName", event.get("cityName", "TBD"))
    min_price = event.get("minPrice", 0)
    max_price = event.get("maxPrice", min_price)
    age_restriction = event.get("age", event.get("ageRestriction", 0))

    age_text = get_age_restriction_text(age_restriction, lang)

    # Calculate countdown to event start
    countdown = calculate_countdown(event_date_str, lang)
    countdown_text = ""
    if countdown:
        countdown_text = get_text("countdown_label", lang, countdown=countdown)

    return get_text(
        "event_details",
        lang,
        name=event_name,
        date=event_date,
        venue=venue,
        min_price=min_price,
        max_price=max_price,
        age_restriction=age_text,
        countdown=countdown_text
    )


def build_event_details_keyboard(
    event_id: int,
    lang: str,
    agent_fid: int = 0,
    chat_id: int = 0,
) -> InlineKeyboardMarkup:
    """Build keyboard for event details with buy and back buttons."""
    builder = InlineKeyboardBuilder()

    # Buy ticket button — handled by purchase_handlers via callback
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_buy_ticket", lang),
            callback_data=f"buy_{event_id}"
        )
    )

    # Back to events list button
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back_to_events", lang),
            callback_data="back_to_events"
        )
    )

    return builder.as_markup()


@router.callback_query(F.data.startswith("event_"))
async def callback_event_details(callback: CallbackQuery):
    """Handle event selection - show event details."""
    telegram_user = callback.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    # Extract event ID from callback data
    try:
        event_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer(get_text("error_event_not_found", lang))
        return

    await callback.answer()

    async for session in get_async_session():
        # Get user and their current agent
        result = await session.execute(
            select(User).where(User.telegram_chat_id == telegram_user.id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.current_agent_id:
            await callback.message.edit_text(get_text("error_no_agent", lang))
            return

        lang = user.preferred_language or lang

        # Get agent
        result = await session.execute(
            select(Agent).where(Agent.id == user.current_agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            await callback.message.edit_text(get_text("error_no_agent", lang))
            return

        # Check if agent is active
        if not agent.is_active:
            await callback.message.edit_text(get_text("error_agent_inactive", lang))
            return

        try:
            # Fetch events from Bill24
            events = await fetch_events_from_bill24(agent)

            # Find the selected event
            event = next((e for e in events if e.get("actionId") == event_id), None)

            if not event:
                await callback.message.edit_text(get_text("error_event_not_found", lang))
                return

            # Build message and keyboard
            message_text = build_event_details_message(event, lang)
            keyboard = build_event_details_keyboard(
                event_id, lang,
                agent_fid=agent.fid,
                chat_id=telegram_user.id,
            )

            # Send event poster if available, otherwise just text
            poster_url = event.get("bigPosterUrl") or event.get("smallPosterUrl")
            if poster_url:
                # Delete old message (can't edit text into photo)
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.message.answer_photo(
                    photo=URLInputFile(poster_url),
                    caption=message_text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
            else:
                await callback.message.edit_text(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )

        except Bill24Error as e:
            logger.error(f"Failed to fetch event details: {e}")
            try:
                await callback.message.edit_text(get_text("error_fetching_events", lang))
            except Exception:
                await callback.message.answer(get_text("error_fetching_events", lang))
        except Exception as e:
            logger.exception(f"Unexpected error fetching event details: {e}")
            try:
                await callback.message.edit_text(get_text("error_general", lang))
            except Exception:
                await callback.message.answer(get_text("error_general", lang))


@router.callback_query(F.data == "back_to_events")
async def callback_back_to_events(callback: CallbackQuery):
    """Handle back to events list callback."""
    telegram_user = callback.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    await callback.answer()

    async for session in get_async_session():
        # Get user and their current agent
        result = await session.execute(
            select(User).where(User.telegram_chat_id == telegram_user.id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.current_agent_id:
            await callback.message.edit_text(get_text("error_no_agent", lang))
            return

        lang = user.preferred_language or lang

        # Get agent
        result = await session.execute(
            select(Agent).where(Agent.id == user.current_agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            await callback.message.edit_text(get_text("error_no_agent", lang))
            return

        # Check if agent is active
        if not agent.is_active:
            await callback.message.edit_text(get_text("error_agent_inactive", lang))
            return

        try:
            # Fetch events from Bill24
            events = await fetch_events_from_bill24(agent)

            if not events:
                await callback.message.edit_text(get_text("no_events", lang))
                return

            # Get first page
            page_events, total_pages = get_page_events(events, page=1)

            # Build message and keyboard
            message_text = build_events_list_message(page_events, page=1, total_pages=total_pages, lang=lang)
            keyboard = build_events_pagination_keyboard(page_events, page=1, total_pages=total_pages, lang=lang)

            # If current message is a photo (from event details with poster), delete and send new
            if callback.message.photo:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.message.answer(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                await callback.message.edit_text(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )

        except Bill24Error as e:
            logger.error(f"Failed to fetch events: {e}")
            await callback.message.edit_text(get_text("error_fetching_events", lang))
        except Exception as e:
            logger.exception(f"Unexpected error fetching events: {e}")
            await callback.message.edit_text(get_text("error_general", lang))


@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery):
    """Handle back to main menu callback."""
    telegram_user = callback.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    await callback.answer()

    async for session in get_async_session():
        result = await session.execute(
            select(User).where(User.telegram_chat_id == telegram_user.id)
        )
        user = result.scalar_one_or_none()

        if user:
            lang = user.preferred_language or lang
            has_agent = user.current_agent_id is not None
        else:
            has_agent = False

        await callback.message.edit_text(
            get_text("welcome", lang),
            reply_markup=get_main_keyboard(lang, has_agent=has_agent),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    """Handle no-op callbacks (like page number display)."""
    await callback.answer()


@router.message(F.text.startswith("/"))
async def cmd_unknown(message: Message):
    """Handle unknown commands - suggest /help."""
    telegram_user = message.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    await message.answer(get_text("unknown_command", lang))


@router.message()
async def msg_unknown(message: Message):
    """Handle any other messages - suggest /help."""
    telegram_user = message.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    await message.answer(get_text("unknown_message", lang))


def register_handlers(dp):
    """Register all handlers with the dispatcher."""
    # Purchase router first — it handles buy_ callbacks (FSM-based purchase flow)
    try:
        from app.bot.purchase_handlers import purchase_router
    except ModuleNotFoundError:
        from backend.app.bot.purchase_handlers import purchase_router
    dp.include_router(purchase_router)
    dp.include_router(router)
    logger.info("Bot handlers registered")
