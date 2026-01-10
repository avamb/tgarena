"""
Test Telegram bot /start command.

Tests that the bot responds correctly to /start with proper welcome message.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestStartCommandHandler:
    """Test /start command handler exists and works."""

    def test_cmd_start_handler_exists(self):
        """Test cmd_start handler function exists."""
        from app.bot.handlers import cmd_start
        import inspect

        assert callable(cmd_start)
        assert inspect.iscoroutinefunction(cmd_start)

    @pytest.mark.asyncio
    async def test_start_command_responds(self):
        """Test /start command sends a response."""
        from app.bot.handlers import cmd_start

        message = AsyncMock()
        message.text = "/start"
        message.from_user = MagicMock()
        message.from_user.id = 123456789
        message.from_user.username = "testuser"
        message.from_user.first_name = "Test"
        message.from_user.last_name = "User"
        message.from_user.language_code = "en"
        message.answer = AsyncMock()

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_user = MagicMock()
            mock_user.preferred_language = "en"
            mock_user.current_agent_id = None
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            await cmd_start(message)

            # Should send a response
            message.answer.assert_called()


class TestWelcomeMessage:
    """Test welcome message content."""

    def test_welcome_message_exists(self):
        """Test welcome message exists in localization."""
        from app.bot.localization import get_text

        text_ru = get_text("welcome", "ru")
        text_en = get_text("welcome", "en")

        assert text_ru != "welcome"
        assert text_en != "welcome"
        assert len(text_ru) > 0
        assert len(text_en) > 0

    def test_welcome_has_bot_name(self):
        """Test welcome mentions bot name."""
        from app.bot.localization import get_text

        text_ru = get_text("welcome", "ru")
        text_en = get_text("welcome", "en")

        # Should mention TG-Ticket-Agent or similar
        assert "TG-Ticket-Agent" in text_ru or "ticket" in text_ru.lower()
        assert "TG-Ticket-Agent" in text_en or "ticket" in text_en.lower()

    def test_welcome_has_emoji(self):
        """Test welcome message has emoji."""
        from app.bot.localization import get_text

        text_ru = get_text("welcome", "ru")

        # Should have ticket emoji
        assert "🎫" in text_ru


class TestLanguageDetection:
    """Test correct language is used for welcome."""

    @pytest.mark.asyncio
    async def test_russian_user_gets_russian_message(self):
        """Test Russian Telegram user gets Russian welcome."""
        from app.bot.handlers import cmd_start
        from app.bot.localization import get_text

        message = AsyncMock()
        message.text = "/start"
        message.from_user = MagicMock()
        message.from_user.id = 111222333
        message.from_user.username = "russianuser"
        message.from_user.first_name = "Ivan"
        message.from_user.last_name = None
        message.from_user.language_code = "ru"
        message.answer = AsyncMock()

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_user = MagicMock()
            mock_user.preferred_language = "ru"
            mock_user.current_agent_id = None
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            await cmd_start(message)

            # Verify answer was called
            message.answer.assert_called()

            # Get the message that was sent
            call_args = message.answer.call_args
            sent_text = call_args[0][0]

            # Should be Russian text
            expected_ru = get_text("welcome", "ru")
            assert sent_text == expected_ru

    @pytest.mark.asyncio
    async def test_english_user_gets_english_message(self):
        """Test English Telegram user gets English welcome."""
        from app.bot.handlers import cmd_start
        from app.bot.localization import get_text

        message = AsyncMock()
        message.text = "/start"
        message.from_user = MagicMock()
        message.from_user.id = 444555666
        message.from_user.username = "englishuser"
        message.from_user.first_name = "John"
        message.from_user.last_name = "Doe"
        message.from_user.language_code = "en"
        message.answer = AsyncMock()

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_user = MagicMock()
            mock_user.preferred_language = "en"
            mock_user.current_agent_id = None
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            await cmd_start(message)

            message.answer.assert_called()
            call_args = message.answer.call_args
            sent_text = call_args[0][0]

            expected_en = get_text("welcome", "en")
            assert sent_text == expected_en


class TestStartWithDeepLink:
    """Test /start with deep link parameter."""

    @pytest.mark.asyncio
    async def test_start_with_agent_deep_link(self):
        """Test /start with agent deep link shows agent welcome."""
        from app.bot.handlers import cmd_start
        from app.bot.localization import get_text

        message = AsyncMock()
        message.text = "/start agent_1271"  # Deep link with agent FID
        message.from_user = MagicMock()
        message.from_user.id = 777888999
        message.from_user.username = "deeplinker"
        message.from_user.first_name = "Deep"
        message.from_user.last_name = "Link"
        message.from_user.language_code = "en"
        message.answer = AsyncMock()

        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"
        mock_agent.is_active = True
        mock_agent.id = 1

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()

            call_count = [0]
            def get_result():
                call_count[0] += 1
                result = MagicMock()
                if call_count[0] == 1:
                    # User lookup
                    mock_user = MagicMock()
                    mock_user.preferred_language = "en"
                    mock_user.current_agent_id = None
                    result.scalar_one_or_none.return_value = mock_user
                else:
                    # Agent lookup
                    result.scalar_one_or_none.return_value = mock_agent
                return result

            mock_session.execute.side_effect = lambda *args: get_result()

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            await cmd_start(message)

            message.answer.assert_called()
            call_args = message.answer.call_args
            sent_text = call_args[0][0]

            # Should include agent name
            assert "Test Agent" in sent_text


class TestStartCommandKeyboard:
    """Test keyboard is shown with start command."""

    @pytest.mark.asyncio
    async def test_start_shows_main_keyboard(self):
        """Test /start shows main menu keyboard."""
        from app.bot.handlers import cmd_start

        message = AsyncMock()
        message.text = "/start"
        message.from_user = MagicMock()
        message.from_user.id = 100200300
        message.from_user.username = "kbuser"
        message.from_user.first_name = "KB"
        message.from_user.last_name = None
        message.from_user.language_code = "ru"
        message.answer = AsyncMock()

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_user = MagicMock()
            mock_user.preferred_language = "ru"
            mock_user.current_agent_id = None
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            await cmd_start(message)

            # Check reply_markup was passed
            call_kwargs = message.answer.call_args[1]
            assert "reply_markup" in call_kwargs
            assert call_kwargs["reply_markup"] is not None


class TestRouterRegistration:
    """Test start command is registered with router."""

    def test_command_start_filter(self):
        """Test CommandStart filter is used."""
        from app.bot.handlers import router
        from aiogram.filters import CommandStart

        # Router should have handlers registered
        assert router is not None

        # Check router has message handlers
        handlers = router.message.handlers
        assert len(handlers) > 0

    def test_router_includes_cmd_start(self):
        """Test router includes cmd_start handler."""
        from app.bot import handlers
        import inspect

        source = inspect.getsource(handlers)

        # Should have CommandStart filter
        assert "CommandStart" in source
        assert "cmd_start" in source


class TestNewUserCreation:
    """Test new user is created on first /start."""

    @pytest.mark.asyncio
    async def test_new_user_created(self):
        """Test new user is created when not exists."""
        from app.bot.handlers import get_or_create_user

        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 999111222
        message.from_user.username = "newbie"
        message.from_user.first_name = "New"
        message.from_user.last_name = "User"
        message.from_user.language_code = "fr"  # French -> English

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing user
        mock_session.execute.return_value = mock_result

        with patch('app.bot.handlers.User') as MockUser:
            mock_user_instance = MagicMock()
            MockUser.return_value = mock_user_instance

            await get_or_create_user(mock_session, message)

            # User should be created
            MockUser.assert_called_once()
            mock_session.add.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
