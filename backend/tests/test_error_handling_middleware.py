"""
Tests for Global Error Handling Middleware

Tests that the ErrorHandlingMiddleware:
1. Catches unhandled exceptions and sends fallback messages to users
2. Handles DB unavailability gracefully
3. Handles Bill24 API errors gracefully
4. Logs errors with proper context
"""

import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram.types import Message, CallbackQuery, Update

from app.bot.middleware import ErrorHandlingMiddleware, FALLBACK_ERROR_MESSAGE
from app.bot.localization import get_text


@pytest.fixture
def middleware():
    return ErrorHandlingMiddleware()


def make_mock_message(user_id=123456, language_code="ru"):
    """Create a mock Telegram Message that passes isinstance checks."""
    msg = AsyncMock(spec=Message)
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.language_code = language_code
    msg.answer = AsyncMock()
    return msg


def make_mock_callback_query(user_id=123456, language_code="ru"):
    """Create a mock Telegram CallbackQuery that passes isinstance checks."""
    cb = AsyncMock(spec=CallbackQuery)
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.from_user.language_code = language_code
    cb.answer = AsyncMock()
    cb.message = AsyncMock(spec=Message)
    cb.message.answer = AsyncMock()
    return cb


def make_mock_update(message=None, callback_query=None):
    """Create a mock Telegram Update that passes isinstance checks."""
    update = MagicMock(spec=Update)
    update.message = message
    update.callback_query = callback_query
    return update


class TestErrorHandlingMiddleware:
    """Test suite for ErrorHandlingMiddleware."""

    @pytest.mark.asyncio
    async def test_successful_handler_passes_through(self, middleware):
        """Test that successful handler calls pass through normally."""
        message = make_mock_message()
        handler = AsyncMock(return_value="success")

        result = await middleware(handler, message, {})

        assert result == "success"
        handler.assert_called_once_with(message, {})
        # Should NOT send fallback message
        message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_db_unavailable_sends_fallback_message(self, middleware):
        """
        Test: Simulate DB unavailability → verify middleware sends fallback message.

        When a handler raises an exception (e.g., DB connection refused),
        the middleware should catch it and send the user an error message
        instead of silently failing.
        """
        message = make_mock_message(user_id=999, language_code="ru")

        # Simulate DB connection error
        async def failing_handler(event, data):
            raise ConnectionRefusedError("could not connect to server: Connection refused")

        result = await middleware(failing_handler, message, {})

        # Middleware should have sent fallback message
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert call_args == get_text("error_general", "ru")
        assert result is None

    @pytest.mark.asyncio
    async def test_db_unavailable_sends_fallback_english(self, middleware):
        """Test fallback message is sent in English for English users."""
        message = make_mock_message(user_id=999, language_code="en")

        async def failing_handler(event, data):
            raise ConnectionRefusedError("PostgreSQL unavailable")

        result = await middleware(failing_handler, message, {})

        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert call_args == get_text("error_general", "en")

    @pytest.mark.asyncio
    async def test_bill24_api_error_sends_fallback(self, middleware):
        """
        Test: Simulate Bill24 API error → verify user gets error message.

        When Bill24 API fails and the error propagates unhandled,
        the middleware catches it and notifies the user.
        """
        message = make_mock_message(user_id=777, language_code="ru")

        async def failing_handler(event, data):
            raise Exception("Bill24 API timeout: Connection timed out")

        result = await middleware(failing_handler, message, {})

        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert call_args == get_text("error_general", "ru")

    @pytest.mark.asyncio
    async def test_callback_query_error_sends_fallback(self, middleware):
        """Test that errors in callback query handlers also send fallback."""
        callback = make_mock_callback_query(user_id=555, language_code="en")

        async def failing_handler(event, data):
            raise RuntimeError("Something went wrong")

        result = await middleware(failing_handler, callback, {})

        # Should acknowledge callback and send message
        callback.answer.assert_called_once()
        callback.message.answer.assert_called_once()
        call_args = callback.message.answer.call_args[0][0]
        assert call_args == get_text("error_general", "en")

    @pytest.mark.asyncio
    async def test_update_with_message_error_sends_fallback(self, middleware):
        """Test error handling at the Update level with a message."""
        message = make_mock_message(user_id=111, language_code="ru")
        update = make_mock_update(message=message)

        async def failing_handler(event, data):
            raise Exception("Database connection pool exhausted")

        result = await middleware(failing_handler, update, {})

        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert call_args == get_text("error_general", "ru")

    @pytest.mark.asyncio
    async def test_update_with_callback_error_sends_fallback(self, middleware):
        """Test error handling at the Update level with a callback query."""
        callback = make_mock_callback_query(user_id=222, language_code="en")
        update = make_mock_update(callback_query=callback)

        async def failing_handler(event, data):
            raise Exception("Redis connection lost")

        result = await middleware(failing_handler, update, {})

        callback.answer.assert_called_once()
        callback.message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_logging_includes_context(self, middleware, caplog):
        """Test that errors are logged with user_id, handler name, and traceback."""
        message = make_mock_message(user_id=12345, language_code="ru")

        async def my_failing_handler(event, data):
            raise ValueError("test error message")

        with caplog.at_level(logging.ERROR):
            await middleware(my_failing_handler, message, {})

        # Check that log contains user_id and error info
        assert any("12345" in record.message for record in caplog.records)
        assert any("ValueError" in record.message for record in caplog.records)
        assert any("test error message" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_fallback_message_send_failure_doesnt_crash(self, middleware):
        """Test that if sending the fallback message also fails, middleware doesn't crash."""
        message = make_mock_message(user_id=999)
        # Make answer() raise an exception too
        message.answer = AsyncMock(side_effect=Exception("Telegram API down"))

        async def failing_handler(event, data):
            raise RuntimeError("Original error")

        # Should not raise - middleware handles even the send failure
        result = await middleware(failing_handler, message, {})
        assert result is None

    @pytest.mark.asyncio
    async def test_sqlalchemy_operational_error_handled(self, middleware):
        """Test that SQLAlchemy OperationalError (DB down) is handled."""
        message = make_mock_message(user_id=444, language_code="ru")

        async def failing_handler(event, data):
            # Simulate SQLAlchemy error when DB is down
            raise Exception("(psycopg2.OperationalError) could not connect to server")

        result = await middleware(failing_handler, message, {})

        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert call_args == get_text("error_general", "ru")


class TestStartupHealthCheck:
    """Test the startup health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_function_exists(self):
        """Verify the health check function is importable."""
        from app.bot.runner import check_infrastructure_health
        assert callable(check_infrastructure_health)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
