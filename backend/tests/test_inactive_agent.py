"""
Test inactive agent hides events.

Tests that when an agent is set to inactive, users cannot view events.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.localization import get_text


class TestInactiveAgentHandling:
    """Test that inactive agents block event viewing."""

    @pytest.mark.asyncio
    async def test_view_events_blocked_for_inactive_agent(self):
        """Test that view_events returns error for inactive agent."""
        from app.bot.handlers import callback_view_events

        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.language_code = "en"
        callback.from_user.id = 123456
        callback.message = AsyncMock()

        # Create mock user with agent
        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = 1

        # Create inactive agent
        mock_agent = MagicMock()
        mock_agent.id = 1
        mock_agent.is_active = False  # INACTIVE
        mock_agent.fid = 123
        mock_agent.token = "test"
        mock_agent.zone = "test"

        with patch('app.bot.handlers.get_async_session') as mock_session:
            async def mock_gen():
                session = AsyncMock()

                call_count = [0]
                def get_result():
                    call_count[0] += 1
                    result = MagicMock()
                    if call_count[0] == 1:
                        result.scalar_one_or_none.return_value = mock_user
                    else:
                        result.scalar_one_or_none.return_value = mock_agent
                    return result

                session.execute.side_effect = lambda *args, **kwargs: get_result()
                yield session

            mock_session.return_value = mock_gen()

            await callback_view_events(callback)

            # Should have answered callback
            callback.answer.assert_called()

            # Should have sent error_agent_inactive message
            callback.message.answer.assert_called()
            call_args = callback.message.answer.call_args

            # Check message contains inactive error
            sent_text = call_args[0][0]
            inactive_text = get_text("error_agent_inactive", "en")
            assert sent_text == inactive_text

    @pytest.mark.asyncio
    async def test_event_details_blocked_for_inactive_agent(self):
        """Test that event_details returns error for inactive agent."""
        from app.bot.handlers import callback_event_details

        callback = AsyncMock()
        callback.data = "event_123"
        callback.from_user = MagicMock()
        callback.from_user.language_code = "ru"
        callback.from_user.id = 789012
        callback.message = AsyncMock()

        mock_user = MagicMock()
        mock_user.preferred_language = "ru"
        mock_user.current_agent_id = 2

        mock_agent = MagicMock()
        mock_agent.id = 2
        mock_agent.is_active = False  # INACTIVE

        with patch('app.bot.handlers.get_async_session') as mock_session:
            async def mock_gen():
                session = AsyncMock()
                call_count = [0]
                def get_result():
                    call_count[0] += 1
                    result = MagicMock()
                    if call_count[0] == 1:
                        result.scalar_one_or_none.return_value = mock_user
                    else:
                        result.scalar_one_or_none.return_value = mock_agent
                    return result

                session.execute.side_effect = lambda *args, **kwargs: get_result()
                yield session

            mock_session.return_value = mock_gen()

            await callback_event_details(callback)

            callback.answer.assert_called()
            callback.message.edit_text.assert_called()

            sent_text = callback.message.edit_text.call_args[0][0]
            inactive_text = get_text("error_agent_inactive", "ru")
            assert sent_text == inactive_text

    @pytest.mark.asyncio
    async def test_active_agent_allows_events(self):
        """Test that active agent allows viewing events."""
        from app.bot.handlers import callback_view_events

        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.language_code = "en"
        callback.from_user.id = 456789
        callback.message = AsyncMock()

        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = 1

        mock_agent = MagicMock()
        mock_agent.id = 1
        mock_agent.is_active = True  # ACTIVE
        mock_agent.fid = 123
        mock_agent.token = "test"
        mock_agent.zone = "test"

        with patch('app.bot.handlers.get_async_session') as mock_session:
            with patch('app.bot.handlers.fetch_events_from_bill24', new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = []  # Empty events list

                async def mock_gen():
                    session = AsyncMock()
                    call_count = [0]
                    def get_result():
                        call_count[0] += 1
                        result = MagicMock()
                        if call_count[0] == 1:
                            result.scalar_one_or_none.return_value = mock_user
                        else:
                            result.scalar_one_or_none.return_value = mock_agent
                        return result

                    session.execute.side_effect = lambda *args, **kwargs: get_result()
                    yield session

                mock_session.return_value = mock_gen()

                await callback_view_events(callback)

                # Should have proceeded to fetch events
                mock_fetch.assert_called_once()


class TestInactiveAgentInDeepLink:
    """Test that inactive agents are handled in deep links."""

    @pytest.mark.asyncio
    async def test_inactive_agent_deep_link_shows_error(self):
        """Test that inactive agent in deep link shows error."""
        from app.bot.handlers import cmd_start

        message = AsyncMock()
        message.text = "/start agent_12345"
        message.from_user = MagicMock()
        message.from_user.id = 111222333
        message.from_user.language_code = "en"
        message.from_user.username = "testuser"
        message.from_user.first_name = "Test"
        message.from_user.last_name = None

        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = None

        mock_agent = MagicMock()
        mock_agent.id = 1
        mock_agent.fid = 12345
        mock_agent.is_active = False  # INACTIVE
        mock_agent.name = "Test Agent"

        with patch('app.bot.handlers.get_async_session') as mock_session:
            async def mock_gen():
                session = AsyncMock()

                # get_or_create_user
                user_result = MagicMock()
                user_result.scalar_one_or_none.return_value = mock_user

                # get_agent_by_fid (returns active only)
                agent_result = MagicMock()
                agent_result.scalar_one_or_none.return_value = mock_agent

                call_count = [0]
                def get_result():
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return user_result
                    else:
                        return agent_result

                session.execute.side_effect = lambda *args, **kwargs: get_result()
                yield session

            mock_session.return_value = mock_gen()

            await cmd_start(message)

            # Should have sent a message
            message.answer.assert_called()

            # Check that inactive message was sent
            call_args = message.answer.call_args
            sent_text = call_args[0][0]
            inactive_text = get_text("error_agent_inactive", "en")
            assert sent_text == inactive_text


class TestErrorMessages:
    """Test that error messages exist."""

    def test_error_agent_inactive_ru(self):
        """Test Russian inactive error message."""
        text = get_text("error_agent_inactive", "ru")
        assert text != "error_agent_inactive"
        assert len(text) > 0

    def test_error_agent_inactive_en(self):
        """Test English inactive error message."""
        text = get_text("error_agent_inactive", "en")
        assert text != "error_agent_inactive"
        assert "unavailable" in text.lower()


class TestAgentModel:
    """Test Agent model has is_active field."""

    def test_agent_has_is_active_field(self):
        """Test Agent model has is_active attribute."""
        from app.models import Agent

        # Check the model has the attribute
        assert hasattr(Agent, 'is_active')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
