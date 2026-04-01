"""
Telegram Bot Core Module

Creates and configures the aiogram bot and dispatcher.
"""

import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

try:
    from app.core.config import settings
    from app.bot.middleware import ErrorHandlingMiddleware
except ModuleNotFoundError:
    from backend.app.core.config import settings
    from backend.app.bot.middleware import ErrorHandlingMiddleware

logger = logging.getLogger(__name__)

# Global bot and dispatcher instances
_bot: Optional[Bot] = None
dp = Dispatcher(storage=MemoryStorage())

# Register global error-handling middleware
dp.update.middleware(ErrorHandlingMiddleware())
logger.info("Error handling middleware registered")


def create_bot() -> Bot:
    """Create and configure the Telegram bot instance."""
    global _bot

    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    if _bot is None:
        _bot = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        logger.info("Telegram bot created successfully")

    return _bot


def get_bot() -> Bot:
    """Get the current bot instance or create one if it doesn't exist."""
    global _bot
    if _bot is None:
        return create_bot()
    return _bot
