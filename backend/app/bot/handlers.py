"""
Telegram Bot Handlers Module

Contains all message and callback handlers for the bot.
"""

import logging
import re
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

try:
    from app.bot.localization import get_text, get_user_language
    from app.core.database import get_async_session
    from app.models import Agent, User
except ModuleNotFoundError:
    from backend.app.bot.localization import get_text, get_user_language
    from backend.app.core.database import get_async_session
    from backend.app.models import Agent, User

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

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
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Created new user: chat_id={telegram_user.id}, username={telegram_user.username}")

    return user


async def get_agent_by_fid(session: AsyncSession, fid: int) -> Optional[Agent]:
    """Get agent by Bill24 FID."""
    result = await session.execute(
        select(Agent).where(Agent.fid == fid, Agent.is_active == True)
    )
    return result.scalar_one_or_none()


def parse_deep_link(text: str) -> Optional[int]:
    """
    Parse agent FID from deep link parameter.

    Expected format: agent_12345 where 12345 is the FID.

    Args:
        text: Deep link parameter text

    Returns:
        Agent FID or None if not valid
    """
    if not text:
        return None

    # Match pattern: agent_<fid>
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


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Handle /start command with optional deep link.

    Deep link format: t.me/BotUsername?start=agent_12345
    """
    telegram_user = message.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    # Parse deep link parameter
    args = message.text.split(maxsplit=1)
    deep_link_param = args[1] if len(args) > 1 else None
    agent_fid = parse_deep_link(deep_link_param) if deep_link_param else None

    async for session in get_async_session():
        # Get or create user
        user = await get_or_create_user(session, message)
        lang = user.preferred_language or lang

        agent = None
        if agent_fid:
            # Try to find agent
            agent = await get_agent_by_fid(session, agent_fid)

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
                reply_markup=get_main_keyboard(lang, has_agent=True)
            )
        else:
            # Send general welcome message
            await message.answer(
                get_text("welcome", lang),
                reply_markup=get_main_keyboard(lang, has_agent=user.current_agent_id is not None)
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
    """Handle view events button callback."""
    telegram_user = callback.from_user
    lang = get_user_language(telegram_user.language_code if telegram_user else None)

    await callback.answer()
    # TODO: Implement event listing from Bill24
    await callback.message.answer(get_text("no_events", lang))


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
    dp.include_router(router)
    logger.info("Bot handlers registered")
