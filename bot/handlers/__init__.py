"""
Bot Message Handlers

Handlers for Telegram bot commands and callbacks.
"""

from aiogram import Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message


router = Router()


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message):
    """Handle /start command with agent deep link."""
    # Extract agent ID from deep link parameter
    # Format: ?start=agent_{fid}
    args = message.text.split(maxsplit=1)
    deep_link = args[1] if len(args) > 1 else None

    if deep_link and deep_link.startswith("agent_"):
        try:
            agent_fid = int(deep_link.replace("agent_", ""))
            # TODO: Link user to agent and show events
            await message.answer(
                f"Welcome! You are connected to agent {agent_fid}.\n"
                "Use /events to browse available events."
            )
        except ValueError:
            await message.answer("Invalid agent link. Please use a valid link.")
    else:
        await message.answer(
            "Welcome! Please use an agent link to start browsing events."
        )


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command without deep link."""
    await message.answer(
        "Welcome to TG-Ticket-Agent!\n\n"
        "This bot allows you to purchase event tickets.\n"
        "Please use an agent link to get started.\n\n"
        "Commands:\n"
        "/events - Browse events\n"
        "/mytickets - View your tickets\n"
        "/help - Get help"
    )


@router.message(Command("events"))
async def cmd_events(message: Message):
    """Handle /events command."""
    # TODO: Fetch and display events for user's agent
    await message.answer("Loading events... (Not implemented yet)")


@router.message(Command("mytickets"))
async def cmd_my_tickets(message: Message):
    """Handle /mytickets command."""
    # TODO: Fetch and display user's tickets
    await message.answer("Your tickets will appear here... (Not implemented yet)")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    await message.answer(
        "<b>TG-Ticket-Agent Help</b>\n\n"
        "This bot allows you to purchase event tickets.\n\n"
        "<b>How to use:</b>\n"
        "1. Click an agent link to connect\n"
        "2. Browse available events\n"
        "3. Select seats and purchase\n"
        "4. Receive your tickets here!\n\n"
        "<b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/events - Browse events\n"
        "/mytickets - View your tickets\n"
        "/help - This message\n"
        "/language - Change language"
    )


@router.message(Command("language"))
async def cmd_language(message: Message):
    """Handle /language command."""
    # TODO: Show language selection keyboard
    await message.answer("Language selection not implemented yet.")


@router.callback_query(F.data.startswith("event_"))
async def callback_event(callback: CallbackQuery):
    """Handle event selection callback."""
    event_id = callback.data.replace("event_", "")
    # TODO: Show event details
    await callback.answer(f"Event {event_id} selected")


@router.callback_query(F.data == "next_event")
async def callback_next_event(callback: CallbackQuery):
    """Handle next event navigation."""
    # TODO: Show next event
    await callback.answer("Next event")


@router.callback_query(F.data == "prev_event")
async def callback_prev_event(callback: CallbackQuery):
    """Handle previous event navigation."""
    # TODO: Show previous event
    await callback.answer("Previous event")


def register_handlers(dp: Dispatcher):
    """Register all handlers with dispatcher."""
    dp.include_router(router)
