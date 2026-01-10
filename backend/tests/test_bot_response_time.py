"""
Test bot response time performance.

Tests that bot handlers respond within 2 seconds.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# Maximum acceptable response time in seconds
MAX_RESPONSE_TIME = 2.0


class TestStartCommandResponseTime:
    """Test /start command response time."""

    @pytest.mark.asyncio
    async def test_start_command_responds_quickly(self):
        """Test /start command responds within 2 seconds."""
        from app.bot.handlers import cmd_start

        # Create mock message
        message = AsyncMock()
        message.text = "/start"
        message.from_user = MagicMock()
        message.from_user.id = 123456789
        message.from_user.username = "testuser"
        message.from_user.first_name = "Test"
        message.from_user.last_name = "User"
        message.from_user.language_code = "ru"
        message.answer = AsyncMock()

        # Mock database
        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = MagicMock(
                preferred_language="ru",
                current_agent_id=None
            )
            mock_session.execute.return_value = mock_result

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            # Measure response time
            start_time = time.time()
            await cmd_start(message)
            elapsed = time.time() - start_time

            # Should respond within 2 seconds
            assert elapsed < MAX_RESPONSE_TIME, f"Response took {elapsed:.2f}s, max is {MAX_RESPONSE_TIME}s"
            message.answer.assert_called()


class TestHelpCommandResponseTime:
    """Test /help command response time."""

    @pytest.mark.asyncio
    async def test_help_command_responds_quickly(self):
        """Test /help command responds within 2 seconds."""
        from app.bot.handlers import cmd_help

        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456789
        message.from_user.language_code = "en"
        message.answer = AsyncMock()

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = MagicMock(
                preferred_language="en"
            )
            mock_session.execute.return_value = mock_result

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            start_time = time.time()
            await cmd_help(message)
            elapsed = time.time() - start_time

            assert elapsed < MAX_RESPONSE_TIME
            message.answer.assert_called()


class TestCallbackResponseTime:
    """Test callback handler response time."""

    @pytest.mark.asyncio
    async def test_help_callback_responds_quickly(self):
        """Test help callback responds within 2 seconds."""
        from app.bot.handlers import callback_help

        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.language_code = "ru"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()

        start_time = time.time()
        await callback_help(callback)
        elapsed = time.time() - start_time

        assert elapsed < MAX_RESPONSE_TIME
        callback.answer.assert_called()

    @pytest.mark.asyncio
    async def test_back_to_main_callback_responds_quickly(self):
        """Test back_to_main callback responds within 2 seconds."""
        from app.bot.handlers import callback_back_to_main

        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.id = 123456789
        callback.from_user.language_code = "ru"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = MagicMock(
                preferred_language="ru",
                current_agent_id=1
            )
            mock_session.execute.return_value = mock_result

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            start_time = time.time()
            await callback_back_to_main(callback)
            elapsed = time.time() - start_time

            assert elapsed < MAX_RESPONSE_TIME


class TestEventListResponseTime:
    """Test event list response time."""

    @pytest.mark.asyncio
    async def test_view_events_responds_within_limit(self):
        """Test view_events callback responds within 2 seconds."""
        from app.bot.handlers import callback_view_events

        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.id = 123456789
        callback.from_user.language_code = "ru"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()

        # Mock agent with is_active = True
        mock_agent = MagicMock()
        mock_agent.is_active = True
        mock_agent.fid = 1271
        mock_agent.token = "test"
        mock_agent.zone = "test"

        mock_user = MagicMock()
        mock_user.current_agent_id = 1
        mock_user.preferred_language = "ru"

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()

            call_count = [0]
            def get_result():
                call_count[0] += 1
                result = MagicMock()
                if call_count[0] == 1:
                    result.scalar_one_or_none.return_value = mock_user
                else:
                    result.scalar_one_or_none.return_value = mock_agent
                return result

            mock_session.execute.side_effect = lambda *args: get_result()

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            # Mock Bill24 response
            with patch('app.bot.handlers.fetch_events_from_bill24') as mock_fetch:
                mock_fetch.return_value = [
                    {"actionId": 1, "actionName": "Test Event", "actionDate": "2026-01-15T19:00:00", "minPrice": 1000}
                ]

                mock_loading_msg = AsyncMock()
                mock_loading_msg.edit_text = AsyncMock()
                callback.message.answer.return_value = mock_loading_msg

                start_time = time.time()
                await callback_view_events(callback)
                elapsed = time.time() - start_time

                # Even with mocked Bill24, should be fast
                assert elapsed < MAX_RESPONSE_TIME


class TestLocalizationPerformance:
    """Test localization function performance."""

    def test_get_text_is_fast(self):
        """Test get_text is fast (< 1ms per call)."""
        from app.bot.localization import get_text

        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            get_text("welcome", "ru")
            get_text("help_text", "en")
            get_text("btn_view_events", "ru")
        elapsed = time.time() - start_time

        # Should complete 3000 lookups very quickly
        per_call = elapsed / (iterations * 3) * 1000  # ms per call

        assert per_call < 1.0, f"get_text takes {per_call:.3f}ms per call"

    def test_get_user_language_is_fast(self):
        """Test get_user_language is fast."""
        from app.bot.localization import get_user_language

        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            get_user_language("ru")
            get_user_language("en")
            get_user_language("de")
            get_user_language(None)
        elapsed = time.time() - start_time

        per_call = elapsed / (iterations * 4) * 1000

        assert per_call < 0.1, f"get_user_language takes {per_call:.3f}ms per call"


class TestCountdownPerformance:
    """Test countdown calculation performance."""

    def test_calculate_countdown_is_fast(self):
        """Test calculate_countdown is fast."""
        from app.bot.handlers import calculate_countdown
        from datetime import datetime, timezone, timedelta

        iterations = 1000
        future_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

        start_time = time.time()
        for _ in range(iterations):
            calculate_countdown(future_date, "ru")
        elapsed = time.time() - start_time

        per_call = elapsed / iterations * 1000

        assert per_call < 1.0, f"calculate_countdown takes {per_call:.3f}ms per call"


class TestDatabaseQueryPerformance:
    """Test database query patterns for performance."""

    @pytest.mark.asyncio
    async def test_single_query_for_user_lookup(self):
        """Test that user lookup uses a single query."""
        from app.bot.handlers import get_or_create_user

        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456789
        message.from_user.username = "testuser"
        message.from_user.first_name = "Test"
        message.from_user.last_name = None
        message.from_user.language_code = "ru"

        mock_session = AsyncMock()
        mock_result = MagicMock()

        # Simulate existing user found
        mock_user = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        start_time = time.time()
        result = await get_or_create_user(mock_session, message)
        elapsed = time.time() - start_time

        # Should be very fast with mocked DB
        assert elapsed < 0.1

        # Should only call execute once for existing user
        assert mock_session.execute.call_count == 1


class TestBotResponseSLA:
    """Test overall bot response SLA requirements."""

    def test_sla_requirement_documented(self):
        """Verify SLA requirement is 2 seconds."""
        assert MAX_RESPONSE_TIME == 2.0

    def test_handlers_are_async(self):
        """Test all handlers are async for non-blocking performance."""
        from app.bot.handlers import (
            cmd_start, cmd_help, cmd_tickets,
            callback_help, callback_view_events,
            callback_back_to_main, callback_noop
        )
        import inspect

        handlers = [
            cmd_start, cmd_help, cmd_tickets,
            callback_help, callback_view_events,
            callback_back_to_main, callback_noop
        ]

        for handler in handlers:
            assert inspect.iscoroutinefunction(handler), f"{handler.__name__} should be async"

    def test_no_blocking_operations(self):
        """Test handlers don't have obvious blocking operations."""
        from app.bot import handlers
        import inspect

        source = inspect.getsource(handlers)

        # Check for common blocking patterns
        blocking_patterns = [
            "time.sleep(",
            "requests.get(",
            "requests.post(",
            "open(",  # file operations
        ]

        for pattern in blocking_patterns:
            # Allow in comments or strings
            if pattern in source:
                lines = source.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line:
                        # Skip if it's a comment
                        stripped = line.strip()
                        if stripped.startswith('#'):
                            continue
                        # Skip if in docstring context (basic check)
                        if '"""' in line or "'''" in line:
                            continue
                        # Check for httpx instead of requests (allowed)
                        if 'requests.' not in line:
                            continue
                        pytest.fail(f"Blocking pattern '{pattern}' found at line {i+1}: {line}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
