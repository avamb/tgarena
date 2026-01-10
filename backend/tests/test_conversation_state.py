"""
Test bot conversation state preservation.

Tests that user state (current agent, language) is preserved across sessions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestUserStatePersistence:
    """Test that user state is persisted in database."""

    def test_user_model_has_current_agent_id(self):
        """Test User model has current_agent_id field."""
        from app.models import User
        assert hasattr(User, 'current_agent_id')

    def test_user_model_has_preferred_language(self):
        """Test User model has preferred_language field."""
        from app.models import User
        assert hasattr(User, 'preferred_language')

    def test_user_model_has_telegram_fields(self):
        """Test User model has Telegram-related fields."""
        from app.models import User
        assert hasattr(User, 'telegram_chat_id')
        assert hasattr(User, 'telegram_username')
        assert hasattr(User, 'telegram_first_name')


class TestExistingUserRecognition:
    """Test that existing users are recognized on restart."""

    @pytest.mark.asyncio
    async def test_get_or_create_user_returns_existing(self):
        """Test get_or_create_user returns existing user."""
        from app.bot.handlers import get_or_create_user

        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456789
        message.from_user.username = "existinguser"
        message.from_user.first_name = "Existing"
        message.from_user.last_name = "User"
        message.from_user.language_code = "en"

        # Create mock existing user
        existing_user = MagicMock()
        existing_user.id = 1
        existing_user.telegram_chat_id = 123456789
        existing_user.current_agent_id = 5  # Has an agent linked
        existing_user.preferred_language = "ru"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_session.execute.return_value = mock_result

        user = await get_or_create_user(mock_session, message)

        # Should return existing user
        assert user == existing_user
        assert user.current_agent_id == 5
        assert user.preferred_language == "ru"

        # Should NOT add new user
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_user_creates_new(self):
        """Test get_or_create_user creates new user when not found."""
        from app.bot.handlers import get_or_create_user

        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 987654321
        message.from_user.username = "newuser"
        message.from_user.first_name = "New"
        message.from_user.last_name = None
        message.from_user.language_code = "ru"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing user
        mock_session.execute.return_value = mock_result

        with patch('app.bot.handlers.User') as MockUser:
            mock_new_user = MagicMock()
            MockUser.return_value = mock_new_user

            await get_or_create_user(mock_session, message)

            # Should add new user
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called()


class TestAgentPreservation:
    """Test that current agent is preserved across sessions."""

    @pytest.mark.asyncio
    async def test_start_without_deeplink_keeps_agent(self):
        """Test /start without deeplink keeps existing agent."""
        from app.bot.handlers import cmd_start

        message = AsyncMock()
        message.text = "/start"  # No deep link
        message.from_user = MagicMock()
        message.from_user.id = 111222333
        message.from_user.language_code = "en"
        message.from_user.username = "returninguser"
        message.from_user.first_name = "Returning"
        message.from_user.last_name = None

        # Mock existing user with agent
        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = 10  # Has an agent

        with patch('app.bot.handlers.get_async_session') as mock_session:
            with patch('app.bot.handlers.get_or_create_user', new_callable=AsyncMock) as mock_get_user:
                mock_get_user.return_value = mock_user

                async def mock_gen():
                    yield AsyncMock()

                mock_session.return_value = mock_gen()

                await cmd_start(message)

                # User's agent should still be set
                assert mock_user.current_agent_id == 10

                # Message should have been sent with has_agent=True
                message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_view_events_uses_persisted_agent(self):
        """Test view_events uses agent from user's current_agent_id."""
        from app.bot.handlers import callback_view_events

        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.language_code = "ru"
        callback.from_user.id = 444555666
        callback.message = AsyncMock()

        # Mock user with persisted agent
        mock_user = MagicMock()
        mock_user.preferred_language = "ru"
        mock_user.current_agent_id = 7  # Agent 7 was saved

        # Mock the agent
        mock_agent = MagicMock()
        mock_agent.id = 7
        mock_agent.fid = 12345
        mock_agent.token = "test_token"
        mock_agent.zone = "test"
        mock_agent.is_active = True

        with patch('app.bot.handlers.get_async_session') as mock_session:
            with patch('app.bot.handlers.fetch_events_from_bill24', new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = []

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

                # Should have fetched events using the persisted agent
                mock_fetch.assert_called_once_with(mock_agent)


class TestLanguagePreservation:
    """Test that language preference is preserved."""

    @pytest.mark.asyncio
    async def test_help_uses_user_preferred_language(self):
        """Test /help uses user's preferred language."""
        from app.bot.handlers import cmd_help

        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.language_code = "en"  # Telegram says English
        message.from_user.id = 777888999

        # But user has Russian preference saved
        mock_user = MagicMock()
        mock_user.preferred_language = "ru"  # Saved preference is Russian

        with patch('app.bot.handlers.get_async_session') as mock_session:
            with patch('app.bot.handlers.get_or_create_user', new_callable=AsyncMock) as mock_get_user:
                mock_get_user.return_value = mock_user

                async def mock_gen():
                    yield AsyncMock()

                mock_session.return_value = mock_gen()

                await cmd_help(message)

                # Message should have been sent
                message.answer.assert_called()
                call_args = message.answer.call_args
                sent_text = call_args[0][0]

                # Should be Russian (user preference) not English (Telegram)
                assert "Помощь" in sent_text


class TestGracefulReset:
    """Test that state is gracefully reset when needed."""

    def test_unknown_message_handler_exists(self):
        """Test unknown message handler exists for graceful handling."""
        from app.bot.handlers import msg_unknown
        import inspect
        assert inspect.iscoroutinefunction(msg_unknown)

    def test_unknown_command_handler_exists(self):
        """Test unknown command handler exists for graceful handling."""
        from app.bot.handlers import cmd_unknown
        import inspect
        assert inspect.iscoroutinefunction(cmd_unknown)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
