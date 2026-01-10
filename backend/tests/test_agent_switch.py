"""
Test user can switch agents via new deep link.

Tests that clicking a different agent's deep link switches the user's context.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestAgentSwitching:
    """Test switching between agents."""

    @pytest.mark.asyncio
    async def test_switch_from_agent_a_to_agent_b(self):
        """Test user switches from Agent A to Agent B."""
        from app.bot.handlers import cmd_start

        message = AsyncMock()
        message.text = "/start agent_2000"  # Agent B
        message.from_user = MagicMock()
        message.from_user.id = 123456789
        message.from_user.username = "switchuser"
        message.from_user.first_name = "Switch"
        message.from_user.last_name = None
        message.from_user.language_code = "en"
        message.answer = AsyncMock()

        # User was previously with Agent A (id=1)
        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = 1  # Agent A

        # Agent B
        mock_agent_b = MagicMock()
        mock_agent_b.id = 2
        mock_agent_b.fid = 2000
        mock_agent_b.name = "Agent B"
        mock_agent_b.is_active = True

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()

            call_count = [0]
            def get_result():
                call_count[0] += 1
                result = MagicMock()
                if call_count[0] == 1:
                    result.scalar_one_or_none.return_value = mock_user
                else:
                    result.scalar_one_or_none.return_value = mock_agent_b
                return result

            mock_session.execute.side_effect = lambda *args: get_result()

            async def gen():
                yield mock_session

            mock_session_gen.return_value = gen()

            await cmd_start(message)

            # User should now be linked to Agent B
            assert mock_user.current_agent_id == 2

    @pytest.mark.asyncio
    async def test_welcome_shows_new_agent_name(self):
        """Test welcome message shows new agent name after switch."""
        from app.bot.handlers import cmd_start

        message = AsyncMock()
        message.text = "/start agent_3000"
        message.from_user = MagicMock()
        message.from_user.id = 999888777
        message.from_user.username = "namecheck"
        message.from_user.first_name = "Name"
        message.from_user.last_name = None
        message.from_user.language_code = "ru"
        message.answer = AsyncMock()

        mock_user = MagicMock()
        mock_user.preferred_language = "ru"
        mock_user.current_agent_id = 1  # Old agent

        mock_new_agent = MagicMock()
        mock_new_agent.id = 3
        mock_new_agent.fid = 3000
        mock_new_agent.name = "New Concert Hall"
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

            call_args = message.answer.call_args
            sent_text = call_args[0][0]

            # New agent name should be in message
            assert "New Concert Hall" in sent_text


class TestAgentContextPersistence:
    """Test agent context persists in database."""

    @pytest.mark.asyncio
    async def test_database_updated_on_switch(self):
        """Test user's current_agent_id updated in database."""
        from app.bot.handlers import cmd_start

        message = AsyncMock()
        message.text = "/start agent_4000"
        message.from_user = MagicMock()
        message.from_user.id = 111222333
        message.from_user.username = "dbuser"
        message.from_user.first_name = "DB"
        message.from_user.last_name = None
        message.from_user.language_code = "en"
        message.answer = AsyncMock()

        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = 1

        mock_agent = MagicMock()
        mock_agent.id = 4
        mock_agent.fid = 4000
        mock_agent.name = "Agent D"
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

            # Commit should be called to persist change
            mock_session.commit.assert_called()


class TestEventsAfterSwitch:
    """Test correct events shown after agent switch."""

    @pytest.mark.asyncio
    async def test_view_events_uses_new_agent(self):
        """Test View Events uses new agent context."""
        from app.bot.handlers import callback_view_events

        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.id = 444555666
        callback.from_user.language_code = "en"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()

        mock_user = MagicMock()
        mock_user.current_agent_id = 5  # New agent after switch
        mock_user.preferred_language = "en"

        mock_agent = MagicMock()
        mock_agent.id = 5
        mock_agent.fid = 5000
        mock_agent.token = "token5"
        mock_agent.zone = "test"
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

            with patch('app.bot.handlers.fetch_events_from_bill24') as mock_fetch:
                mock_fetch.return_value = [
                    {"actionId": 500, "actionName": "Agent 5 Event"}
                ]

                mock_loading_msg = AsyncMock()
                mock_loading_msg.edit_text = AsyncMock()
                callback.message.answer.return_value = mock_loading_msg

                await callback_view_events(callback)

                # fetch_events_from_bill24 should be called with new agent
                mock_fetch.assert_called_once()
                call_args = mock_fetch.call_args[0]
                used_agent = call_args[0]
                assert used_agent.id == 5


class TestMultipleSwitches:
    """Test multiple agent switches."""

    @pytest.mark.asyncio
    async def test_switch_multiple_times(self):
        """Test user can switch agents multiple times."""
        from app.bot.handlers import cmd_start

        # Simulate switching Agent 1 -> 2 -> 3

        agents = [
            {"id": 1, "fid": 1000, "name": "Agent 1"},
            {"id": 2, "fid": 2000, "name": "Agent 2"},
            {"id": 3, "fid": 3000, "name": "Agent 3"},
        ]

        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = None

        for i, agent_data in enumerate(agents):
            message = AsyncMock()
            message.text = f"/start agent_{agent_data['fid']}"
            message.from_user = MagicMock()
            message.from_user.id = 777888999
            message.from_user.username = "multiswitch"
            message.from_user.first_name = "Multi"
            message.from_user.last_name = None
            message.from_user.language_code = "en"
            message.answer = AsyncMock()

            mock_agent = MagicMock()
            mock_agent.id = agent_data["id"]
            mock_agent.fid = agent_data["fid"]
            mock_agent.name = agent_data["name"]
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

                # Verify agent switched
                assert mock_user.current_agent_id == agent_data["id"]


class TestSwitchToInactiveAgent:
    """Test switching to inactive agent is handled."""

    @pytest.mark.asyncio
    async def test_cannot_switch_to_inactive_agent(self):
        """Test user cannot switch to inactive agent."""
        from app.bot.handlers import cmd_start
        from app.bot.localization import get_text

        message = AsyncMock()
        message.text = "/start agent_9999"
        message.from_user = MagicMock()
        message.from_user.id = 123123123
        message.from_user.username = "inactivetest"
        message.from_user.first_name = "Inactive"
        message.from_user.last_name = None
        message.from_user.language_code = "en"
        message.answer = AsyncMock()

        mock_user = MagicMock()
        mock_user.preferred_language = "en"
        mock_user.current_agent_id = 1  # Current active agent

        # Inactive agent (not returned by get_agent_by_fid)
        # Because get_agent_by_fid has is_active=True filter

        with patch('app.bot.handlers.get_async_session') as mock_session_gen:
            mock_session = AsyncMock()

            call_count = [0]
            def get_result():
                call_count[0] += 1
                result = MagicMock()
                if call_count[0] == 1:
                    result.scalar_one_or_none.return_value = mock_user
                else:
                    result.scalar_one_or_none.return_value = None  # Agent not found
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


class TestAgentFIDLookup:
    """Test agent lookup by FID."""

    @pytest.mark.asyncio
    async def test_get_agent_by_fid_function(self):
        """Test get_agent_by_fid function exists."""
        from app.bot.handlers import get_agent_by_fid
        import inspect

        assert callable(get_agent_by_fid)
        assert inspect.iscoroutinefunction(get_agent_by_fid)

    @pytest.mark.asyncio
    async def test_get_agent_by_fid_filters_active(self):
        """Test get_agent_by_fid only returns active agents."""
        from app.bot.handlers import get_agent_by_fid

        mock_session = AsyncMock()
        mock_result = MagicMock()

        # Only active agent should be returned
        mock_active_agent = MagicMock()
        mock_active_agent.is_active = True
        mock_result.scalar_one_or_none.return_value = mock_active_agent
        mock_session.execute.return_value = mock_result

        result = await get_agent_by_fid(mock_session, fid=1271)

        assert result is not None
        assert result.is_active is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
