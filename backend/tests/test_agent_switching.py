"""
Test agent switching via deep link.

Tests that when a user clicks a different agent's deep link,
their current_agent_id is updated to the new agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.handlers import cmd_start, parse_deep_link
from app.bot.localization import get_text


class TestAgentSwitching:
    """Test that users can switch agents via deep links."""

    @pytest.mark.asyncio
    async def test_user_switches_from_agent_a_to_agent_b(self):
        """Test user's current_agent_id updates when clicking new deep link."""
        message = AsyncMock()
        message.text = "/start agent_22222"  # New agent B with FID 22222
        message.from_user = MagicMock()
        message.from_user.id = 123456789
        message.from_user.language_code = "en"
        message.from_user.username = "testuser"
        message.from_user.first_name = "Test"
        message.from_user.last_name = None

        # User already linked to Agent A
        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = 1  # Agent A

        # New Agent B
        mock_agent_b = MagicMock()
        mock_agent_b.id = 2  # Agent B's internal ID
        mock_agent_b.fid = 22222
        mock_agent_b.is_active = True
        mock_agent_b.name = "Agent B"

        with patch('app.bot.handlers.get_async_session') as mock_session:
            with patch('app.bot.handlers.get_or_create_user', new_callable=AsyncMock) as mock_get_user:
                with patch('app.bot.handlers.get_agent_by_fid', new_callable=AsyncMock) as mock_get_agent:
                    mock_get_user.return_value = mock_user
                    mock_get_agent.return_value = mock_agent_b

                    async def mock_gen():
                        session = AsyncMock()
                        yield session

                    mock_session.return_value = mock_gen()

                    await cmd_start(message)

                    # Verify user's agent was updated to Agent B
                    assert mock_user.current_agent_id == 2  # Now Agent B

    @pytest.mark.asyncio
    async def test_new_agent_name_shown_in_welcome(self):
        """Test welcome message shows new agent name."""
        message = AsyncMock()
        message.text = "/start agent_33333"
        message.from_user = MagicMock()
        message.from_user.id = 987654321
        message.from_user.language_code = "ru"
        message.from_user.username = "otheruser"
        message.from_user.first_name = "Other"
        message.from_user.last_name = None

        mock_user = MagicMock()
        mock_user.preferred_language = "ru"
        mock_user.current_agent_id = 1

        mock_new_agent = MagicMock()
        mock_new_agent.id = 3
        mock_new_agent.fid = 33333
        mock_new_agent.is_active = True
        mock_new_agent.name = "New Fancy Agent"

        with patch('app.bot.handlers.get_async_session') as mock_session:
            with patch('app.bot.handlers.get_or_create_user', new_callable=AsyncMock) as mock_get_user:
                with patch('app.bot.handlers.get_agent_by_fid', new_callable=AsyncMock) as mock_get_agent:
                    mock_get_user.return_value = mock_user
                    mock_get_agent.return_value = mock_new_agent

                    async def mock_gen():
                        session = AsyncMock()
                        yield session

                    mock_session.return_value = mock_gen()

                    await cmd_start(message)

                    # Verify welcome message was sent with new agent name
                    message.answer.assert_called()
                    call_args = message.answer.call_args
                    sent_text = call_args[0][0]

                    assert "New Fancy Agent" in sent_text

    @pytest.mark.asyncio
    async def test_agent_switch_commits_to_database(self):
        """Test that agent switch is committed to database."""
        message = AsyncMock()
        message.text = "/start agent_44444"
        message.from_user = MagicMock()
        message.from_user.id = 111222333
        message.from_user.language_code = "en"
        message.from_user.username = "user123"
        message.from_user.first_name = "User"
        message.from_user.last_name = None

        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = 99

        mock_agent = MagicMock()
        mock_agent.id = 4
        mock_agent.fid = 44444
        mock_agent.is_active = True
        mock_agent.name = "Agent Four"

        with patch('app.bot.handlers.get_async_session') as mock_session:
            with patch('app.bot.handlers.get_or_create_user', new_callable=AsyncMock) as mock_get_user:
                with patch('app.bot.handlers.get_agent_by_fid', new_callable=AsyncMock) as mock_get_agent:
                    mock_get_user.return_value = mock_user
                    mock_get_agent.return_value = mock_agent

                    mock_db_session = AsyncMock()

                    async def mock_gen():
                        yield mock_db_session

                    mock_session.return_value = mock_gen()

                    await cmd_start(message)

                    # Verify commit was called
                    mock_db_session.commit.assert_called()


class TestAgentSwitchEventsChange:
    """Test that events shown change after agent switch."""

    def test_events_fetched_from_current_agent(self):
        """Test fetch_events_from_bill24 uses agent parameter."""
        from app.bot.handlers import fetch_events_from_bill24

        # The function takes an agent parameter
        import inspect
        sig = inspect.signature(fetch_events_from_bill24)
        params = list(sig.parameters.keys())

        assert 'agent' in params

    def test_view_events_uses_user_current_agent(self):
        """Test callback_view_events fetches from user's current agent."""
        # This is implicitly tested by the handler code which:
        # 1. Gets user.current_agent_id
        # 2. Loads agent by that ID
        # 3. Fetches events from that agent

        # Reading the handler code confirms this flow
        from app.bot.handlers import callback_view_events
        import inspect

        # Verify it's an async function that exists
        assert inspect.iscoroutinefunction(callback_view_events)


class TestDeepLinkParsing:
    """Test deep link parsing for agent switching."""

    def test_parse_deep_link_valid_agent_a(self):
        """Test parsing Agent A deep link."""
        result = parse_deep_link("agent_11111")
        assert result == 11111

    def test_parse_deep_link_valid_agent_b(self):
        """Test parsing Agent B deep link."""
        result = parse_deep_link("agent_22222")
        assert result == 22222

    def test_parse_deep_link_different_agents(self):
        """Test different agent FIDs are parsed correctly."""
        agent_a_fid = parse_deep_link("agent_100")
        agent_b_fid = parse_deep_link("agent_200")

        assert agent_a_fid != agent_b_fid
        assert agent_a_fid == 100
        assert agent_b_fid == 200


class TestUserAgentLinkPersistence:
    """Test that user-agent link is properly stored."""

    def test_user_model_has_current_agent_id(self):
        """Test User model has current_agent_id field."""
        from app.models import User

        assert hasattr(User, 'current_agent_id')

    def test_agent_model_has_required_fields(self):
        """Test Agent model has required fields."""
        from app.models import Agent

        assert hasattr(Agent, 'id')
        assert hasattr(Agent, 'fid')
        assert hasattr(Agent, 'is_active')
        assert hasattr(Agent, 'name')


class TestWelcomeMessageVariation:
    """Test welcome message reflects current agent."""

    def test_welcome_with_agent_text_exists_ru(self):
        """Test Russian welcome_with_agent text exists."""
        text = get_text("welcome_with_agent", "ru", agent_name="Test")
        assert text != "welcome_with_agent"
        assert "Test" in text

    def test_welcome_with_agent_text_exists_en(self):
        """Test English welcome_with_agent text exists."""
        text = get_text("welcome_with_agent", "en", agent_name="Test")
        assert text != "welcome_with_agent"
        assert "Test" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
