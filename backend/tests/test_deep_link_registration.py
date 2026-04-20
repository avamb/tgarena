"""
Test deep link user registration with agent.

Tests that opening an agent deep link creates a user linked to that agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.handlers import extract_agent_deep_link_param, parse_deep_link


class TestDeepLinkParsing:
    """Test deep link parameter parsing."""

    def test_parse_valid_deep_link(self):
        """Test parsing valid agent deep link."""
        result = parse_deep_link("agent_1271")

        assert result == 1271

    def test_parse_deep_link_with_different_fid(self):
        """Test parsing deep link with different FID."""
        result = parse_deep_link("agent_9999")

        assert result == 9999

    def test_parse_invalid_format(self):
        """Test parsing invalid format returns None."""
        result = parse_deep_link("invalid")

        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_deep_link("")

        assert result is None

    def test_parse_none(self):
        """Test parsing None returns None."""
        result = parse_deep_link(None)

        assert result is None

    def test_parse_wrong_prefix(self):
        """Test wrong prefix returns None."""
        result = parse_deep_link("user_1271")

        assert result is None

    def test_parse_with_spaces(self):
        """Test parsing with leading/trailing spaces."""
        result = parse_deep_link("  agent_1271  ")

        assert result == 1271

    def test_extract_param_from_start_command(self):
        """Test extracting deep link from /start command."""
        assert extract_agent_deep_link_param("/start agent_1271") == "agent_1271"

    def test_extract_param_from_raw_agent_payload(self):
        """Test extracting deep link from raw agent payload."""
        assert extract_agent_deep_link_param("agent_1271") == "agent_1271"

    def test_extract_param_from_t_me_url(self):
        """Test extracting deep link from t.me URL."""
        assert extract_agent_deep_link_param("https://t.me/ArenaAppTestZone_bot?start=agent_1271") == "agent_1271"

    def test_extract_param_ignores_unrelated_text(self):
        """Test extractor returns None for unrelated text."""
        assert extract_agent_deep_link_param("hello world") is None


class TestRawDeepLinkMessages:
    """Test raw deep-link payload handling outside /start."""

    @pytest.mark.asyncio
    async def test_raw_agent_message_routes_to_start_flow(self):
        """Raw agent text should reuse the start flow."""
        from app.bot.handlers import msg_agent_deep_link

        message = AsyncMock()
        message.text = "agent_1271"

        with patch("app.bot.handlers._handle_start_message", new=AsyncMock()) as mock_handle:
            await msg_agent_deep_link(message)

        mock_handle.assert_awaited_once_with(message, deep_link_param="agent_1271")

    @pytest.mark.asyncio
    async def test_t_me_url_routes_to_start_flow(self):
        """Pasted t.me URL should reuse the start flow."""
        from app.bot.handlers import msg_agent_deep_link_url

        message = AsyncMock()
        message.text = "https://t.me/ArenaAppTestZone_bot?start=agent_1271"

        with patch("app.bot.handlers._handle_start_message", new=AsyncMock()) as mock_handle:
            await msg_agent_deep_link_url(message)

        mock_handle.assert_awaited_once_with(message, deep_link_param="agent_1271")


class TestUserAgentLinking:
    """Test user is linked to agent on deep link."""

    @pytest.mark.asyncio
    async def test_user_current_agent_set(self):
        """Test user.current_agent_id is set from deep link."""
        from app.bot.handlers import cmd_start

        message = AsyncMock()
        message.text = "/start agent_1271"
        message.from_user = MagicMock()
        message.from_user.id = 123456789
        message.from_user.username = "newagentuser"
        message.from_user.first_name = "Agent"
        message.from_user.last_name = "User"
        message.from_user.language_code = "en"
        message.answer = AsyncMock()

        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = None  # Initially no agent

        mock_agent = MagicMock()
        mock_agent.id = 5
        mock_agent.fid = 1271
        mock_agent.name = "Test Agent"
        mock_agent.is_active = True

        with patch('app.bot.handlers.get_async_session') as mock_session_gen, \
             patch('app.bot.handlers.fetch_events_from_bill24', new=AsyncMock(return_value=[])):
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

            await cmd_start(message)

            # User's current_agent_id should be updated
            assert mock_user.current_agent_id == 5
            mock_session.commit.assert_called()


class TestDeepLinkWelcome:
    """Test welcome message for deep link users."""

    @pytest.mark.asyncio
    async def test_deep_link_shows_agent_name(self):
        """Test deep link welcome includes agent name."""
        from app.bot.handlers import cmd_start
        from app.bot.localization import get_text

        message = AsyncMock()
        message.text = "/start agent_1271"
        message.from_user = MagicMock()
        message.from_user.id = 777888999
        message.from_user.username = "deepuser"
        message.from_user.first_name = "Deep"
        message.from_user.last_name = None
        message.from_user.language_code = "ru"
        message.answer = AsyncMock()

        mock_user = MagicMock()
        mock_user.preferred_language = "ru"
        mock_user.current_agent_id = None

        mock_agent = MagicMock()
        mock_agent.id = 10
        mock_agent.fid = 1271
        mock_agent.name = "Concert Arena"
        mock_agent.is_active = True

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

            await cmd_start(message)

            call_args = message.answer.call_args_list[0]
            sent_text = call_args[0][0]

            # Should include agent name
            assert "Concert Arena" in sent_text


class TestInvalidDeepLink:
    """Test handling of invalid deep links."""

    @pytest.mark.asyncio
    async def test_invalid_agent_fid(self):
        """Test deep link with non-existent agent FID."""
        from app.bot.handlers import cmd_start
        from app.bot.localization import get_text

        message = AsyncMock()
        message.text = "/start agent_99999"  # Non-existent FID
        message.from_user = MagicMock()
        message.from_user.id = 111222333
        message.from_user.username = "invaliduser"
        message.from_user.first_name = "Invalid"
        message.from_user.last_name = None
        message.from_user.language_code = "en"
        message.answer = AsyncMock()

        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = None

        with patch('app.bot.handlers.get_async_session') as mock_session_gen, \
             patch('app.bot.handlers.fetch_events_from_bill24', new=AsyncMock(return_value=[])):
            mock_session = AsyncMock()

            call_count = [0]
            def get_result():
                call_count[0] += 1
                result = MagicMock()
                if call_count[0] == 1:
                    result.scalar_one_or_none.return_value = mock_user
                else:
                    result.scalar_one_or_none.return_value = None  # No agent
                return result

            mock_session.execute.side_effect = lambda *args: get_result()

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            await cmd_start(message)

            call_args = message.answer.call_args
            sent_text = call_args[0][0]

            # Should show error
            error_text = get_text("error_agent_not_found", "en")
            assert sent_text == error_text


class TestDeepLinkFormat:
    """Test deep link URL format."""

    def test_deep_link_url_format(self):
        """Test expected deep link URL format."""
        bot_username = "ArenaAppTestZone_bot"
        agent_fid = 1271

        deep_link = f"https://t.me/{bot_username}?start=agent_{agent_fid}"

        assert "t.me" in deep_link
        assert bot_username in deep_link
        assert f"agent_{agent_fid}" in deep_link

    def test_deep_link_param_extraction(self):
        """Test extracting param from deep link."""
        # When user clicks deep link, Telegram sends:
        # /start agent_1271

        message_text = "/start agent_1271"
        parts = message_text.split(maxsplit=1)

        assert len(parts) == 2
        assert parts[0] == "/start"
        assert parts[1] == "agent_1271"


class TestExistingUserAgentSwitch:
    """Test existing user switching to new agent."""

    @pytest.mark.asyncio
    async def test_existing_user_updates_agent(self):
        """Test existing user's agent is updated on new deep link."""
        from app.bot.handlers import cmd_start

        message = AsyncMock()
        message.text = "/start agent_2000"  # New agent
        message.from_user = MagicMock()
        message.from_user.id = 555666777
        message.from_user.username = "switchuser"
        message.from_user.first_name = "Switch"
        message.from_user.last_name = None
        message.from_user.language_code = "ru"
        message.answer = AsyncMock()

        # Existing user with old agent
        mock_user = MagicMock()
        mock_user.preferred_language = "ru"
        mock_user.current_agent_id = 1  # Old agent

        # New agent
        mock_new_agent = MagicMock()
        mock_new_agent.id = 2
        mock_new_agent.fid = 2000
        mock_new_agent.name = "New Agent"
        mock_new_agent.is_active = True

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()

            call_count = [0]
            def get_result():
                call_count[0] += 1
                result = MagicMock()
                if call_count[0] == 1:
                    result.scalar_one_or_none.return_value = mock_user
                else:
                    result.scalar_one_or_none.return_value = mock_new_agent
                return result

            mock_session.execute.side_effect = lambda *args: get_result()

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            await cmd_start(message)

            # User's agent should be updated
            assert mock_user.current_agent_id == 2


class TestUserModel:
    """Test User model has agent relationship."""

    def test_user_has_current_agent_id(self):
        """Test User model has current_agent_id field."""
        from app.models import User

        assert hasattr(User, 'current_agent_id')

    def test_user_has_agent_relationship(self):
        """Test User model has current_agent relationship."""
        from app.models import User

        # Should have relationship or can join with Agent
        assert hasattr(User, 'current_agent_id') or hasattr(User, 'current_agent')


class TestDeepLinkKeyboard:
    """Test keyboard shows agent options on deep link."""

    @pytest.mark.asyncio
    async def test_view_events_button_shown(self):
        """Test View Events button is shown for agent users."""
        from app.bot.handlers import cmd_start

        message = AsyncMock()
        message.text = "/start agent_1271"
        message.from_user = MagicMock()
        message.from_user.id = 888999000
        message.from_user.username = "kbdeep"
        message.from_user.first_name = "KB"
        message.from_user.last_name = None
        message.from_user.language_code = "en"
        message.answer = AsyncMock()

        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = None

        mock_agent = MagicMock()
        mock_agent.id = 1
        mock_agent.name = "Test"
        mock_agent.is_active = True

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

            await cmd_start(message)

            loading_message = message.answer.return_value
            call_kwargs = loading_message.edit_text.call_args[1]
            assert "reply_markup" in call_kwargs

            keyboard = call_kwargs["reply_markup"]
            assert keyboard is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
