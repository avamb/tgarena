"""
Error Handling Middleware for Telegram Bot

Catches all unhandled exceptions in bot handlers and sends a fallback
message to the user instead of silently failing.
"""

import logging
import traceback
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update

try:
    from app.bot.localization import get_text, get_user_language
except ModuleNotFoundError:
    from backend.app.bot.localization import get_text, get_user_language

logger = logging.getLogger(__name__)

# Fallback message when we can't determine user's language
FALLBACK_ERROR_MESSAGE = "Произошла ошибка, попробуйте позже / An error occurred, please try again later."


class ErrorHandlingMiddleware(BaseMiddleware):
    """
    Global error-handling middleware for aiogram.

    Intercepts all unhandled exceptions in handlers and:
    1. Logs the error with full context (user_id, handler, traceback)
    2. Sends a user-friendly fallback message
    3. Prevents the bot from silently failing
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            # Extract user context for logging
            user_id = self._get_user_id(event)
            handler_name = handler.__name__ if hasattr(handler, '__name__') else str(handler)

            # Log the error with full context
            logger.error(
                f"Unhandled exception in handler '{handler_name}' "
                f"for user_id={user_id}: {type(e).__name__}: {e}",
                exc_info=True,
            )

            # Send fallback message to user
            await self._send_fallback_message(event)

            # Don't re-raise - we've handled it by notifying the user
            return None

    def _get_user_id(self, event: TelegramObject) -> str:
        """Extract user ID from the event for logging context."""
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

    def _get_user_language_code(self, event: TelegramObject) -> str:
        """Extract user's language code from the event."""
        try:
            if isinstance(event, Update):
                if event.message and event.message.from_user:
                    return get_user_language(event.message.from_user.language_code)
                if event.callback_query and event.callback_query.from_user:
                    return get_user_language(event.callback_query.from_user.language_code)
            if isinstance(event, Message) and event.from_user:
                return get_user_language(event.from_user.language_code)
            if isinstance(event, CallbackQuery) and event.from_user:
                return get_user_language(event.from_user.language_code)
        except Exception:
            pass
        return "ru"

    async def _send_fallback_message(self, event: TelegramObject) -> None:
        """Send a fallback error message to the user."""
        try:
            lang = self._get_user_language_code(event)
            error_message = get_text("error_general", lang)

            if isinstance(event, Update):
                # Handle Update objects (outer middleware level)
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
