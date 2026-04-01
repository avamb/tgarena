"""
Bot Middlewares

Middlewares for rate limiting, user tracking, localization, and global error handling.
"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import Dispatcher
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery

logger = logging.getLogger(__name__)

# Fallback error messages (bilingual)
ERROR_MESSAGES = {
    "ru": "Произошла ошибка, попробуйте позже.",
    "en": "An error occurred, please try again later.",
}


class ErrorHandlingMiddleware(BaseMiddleware):
    """
    Global error-handling middleware for the Telegram bot.

    Intercepts all unhandled exceptions in handlers and:
    1. Logs the error with full context (user_id, handler, traceback)
    2. Sends a user-friendly fallback message to the user
    3. Prevents the bot from silently failing
    """

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            # Extract user context for logging
            user_id = self._get_user_id(event)
            handler_name = getattr(handler, '__name__', str(handler))

            # Log the error with full context at ERROR level
            logger.error(
                f"Unhandled exception in handler '{handler_name}' "
                f"for user_id={user_id}: {type(e).__name__}: {e}",
                exc_info=True,
            )

            # Send fallback message to user
            await self._send_fallback_message(event)

            # Don't re-raise - we've handled it by notifying the user
            return None

    def _get_user_id(self, event: Update) -> str:
        """Extract user ID from the Update for logging context."""
        try:
            if isinstance(event, Update):
                if event.message and event.message.from_user:
                    return str(event.message.from_user.id)
                if event.callback_query and event.callback_query.from_user:
                    return str(event.callback_query.from_user.id)
            if isinstance(event, Message) and event.from_user:
                return str(event.from_user.id)
            if isinstance(event, CallbackQuery) and event.from_user:
                return str(event.from_user.id)
        except Exception:
            pass
        return "unknown"

    def _get_user_lang(self, event: Update) -> str:
        """Extract user's language code from the Update."""
        try:
            user = None
            if isinstance(event, Update):
                if event.message and event.message.from_user:
                    user = event.message.from_user
                elif event.callback_query and event.callback_query.from_user:
                    user = event.callback_query.from_user
            elif isinstance(event, Message) and event.from_user:
                user = event.from_user
            elif isinstance(event, CallbackQuery) and event.from_user:
                user = event.from_user

            if user and user.language_code and user.language_code.startswith("ru"):
                return "ru"
        except Exception:
            pass
        return "en"

    async def _send_fallback_message(self, event: Update) -> None:
        """Send a fallback error message to the user."""
        try:
            lang = self._get_user_lang(event)
            error_message = ERROR_MESSAGES.get(lang, ERROR_MESSAGES["en"])

            if isinstance(event, Update):
                if event.message:
                    await event.message.answer(error_message)
                    return
                if event.callback_query:
                    await event.callback_query.answer()
                    try:
                        await event.callback_query.message.answer(error_message)
                    except Exception:
                        pass
                    return

            if isinstance(event, Message):
                await event.answer(error_message)
                return

            if isinstance(event, CallbackQuery):
                await event.answer()
                try:
                    await event.message.answer(error_message)
                except Exception:
                    pass
                return

        except Exception as send_error:
            # Last resort - if even sending the error message fails, just log it
            logger.error(
                f"Failed to send fallback error message to user: {send_error}",
                exc_info=True,
            )


class ThrottlingMiddleware(BaseMiddleware):
    """Simple rate limiting middleware."""

    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self._last_request: dict = {}

    async def __call__(self, handler, event: Update, data: dict):
        # TODO: Implement actual rate limiting with Redis
        return await handler(event, data)


class UserTrackingMiddleware(BaseMiddleware):
    """Middleware to track user activity."""

    async def __call__(self, handler, event: Update, data: dict):
        # TODO: Update user's last_active_at
        return await handler(event, data)


class LocalizationMiddleware(BaseMiddleware):
    """Middleware for message localization."""

    async def __call__(self, handler, event: Update, data: dict):
        # TODO: Load user's preferred language
        data["locale"] = "ru"  # Default to Russian
        return await handler(event, data)


def register_middlewares(dp: Dispatcher):
    """Register all middlewares with dispatcher."""
    # Error handling must be first (outermost) - catches errors from all other middlewares and handlers
    dp.update.middleware(ErrorHandlingMiddleware())
    dp.update.middleware(ThrottlingMiddleware())
    dp.update.middleware(UserTrackingMiddleware())
    dp.update.middleware(LocalizationMiddleware())
    logger.info("Bot middlewares registered (including error handling)")
