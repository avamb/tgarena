"""
TG-Ticket-Agent Bot Entry Point

Starts the aiogram bot with polling or webhook mode.
"""

import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    """Set bot commands for menu."""
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="events", description="Browse events"),
        BotCommand(command="mytickets", description="View my tickets"),
        BotCommand(command="help", description="Get help"),
        BotCommand(command="language", description="Change language"),
    ]
    await bot.set_my_commands(commands)


async def main():
    """Main function to start the bot."""
    # Get token from environment
    token = getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    # Create bot instance
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Create dispatcher
    dp = Dispatcher()

    # Register handlers
    from bot.handlers import register_handlers

    register_handlers(dp)

    # Register middlewares
    from bot.middlewares import register_middlewares

    register_middlewares(dp)

    # Set commands
    await set_commands(bot)

    logger.info("Starting bot...")

    # Start polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
