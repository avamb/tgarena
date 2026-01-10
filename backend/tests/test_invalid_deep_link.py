"""
Test invalid agent deep link handling.

Tests that invalid or non-existent agent deep links are handled gracefully.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.handlers import parse_deep_link, cmd_start
from app.bot.localization import get_text


class TestDeepLinkParsing:
    """Test deep link parameter parsing."""

    def test_parse_valid_agent_deep_link(self):
        """Test parsing valid agent_12345 format."""
        result = parse_deep_link("agent_12345")
        assert result == 12345

    def test_parse_valid_agent_deep_link_large_id(self):
        """Test parsing agent with large ID."""
        result = parse_deep_link("agent_999888777666")
        assert result == 999888777666

    def test_parse_invalid_format_no_underscore(self):
        """Test parsing invalid format without underscore."""
        result = parse_deep_link("agent12345")
        assert result is None

    def test_parse_invalid_format_wrong_prefix(self):
        """Test parsing invalid format with wrong prefix."""
        result = parse_deep_link("user_12345")
        assert result is None

    def test_parse_invalid_format_non_numeric(self):
        """Test parsing invalid format with non-numeric ID."""
        result = parse_deep_link("agent_abc")
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_deep_link("")
        assert result is None

    def test_parse_none(self):
        """Test parsing None."""
        result = parse_deep_link(None)
        assert result is None

    def test_parse_with_whitespace(self):
        """Test parsing with leading/trailing whitespace."""
        result = parse_deep_link("  agent_12345  ")
        assert result == 12345

    def test_parse_random_text(self):
        """Test parsing random text."""
        result = parse_deep_link("hello_world")
        assert result is None

    def test_parse_partial_match(self):
        """Test parsing partial match - agent_ without number."""
        result = parse_deep_link("agent_")
        assert result is None


class TestInvalidAgentHandling:
    """Test handling of invalid agent deep links in cmd_start."""

    @pytest.mark.asyncio
    async def test_nonexistent_agent_shows_error(self):
        """Test that non-existent agent ID shows error message."""
        message = AsyncMock()
        message.text = "/start agent_99999"  # Non-existent agent
        message.from_user = MagicMock()
        message.from_user.id = 123456789
        message.from_user.language_code = "ru"
        message.from_user.username = "testuser"
        message.from_user.first_name = "Test"
        message.from_user.last_name = None

        # Mock database session
        with patch('app.bot.handlers.get_async_session') as mock_session:
            async def mock_gen():
                session = AsyncMock()
                # First call: get_or_create_user - return existing user
                user_mock = MagicMock()
                user_mock.preferred_language = "ru"
                user_mock.current_agent_id = None

                # Second call: get_agent_by_fid - return None (not found)
                call_count = [0]
                def get_result():
                    call_count[0] += 1
                    result = MagicMock()
                    if call_count[0] == 1:
                        # First call - user lookup
                        result.scalar_one_or_none.return_value = user_mock
                    else:
                        # Second call - agent lookup
                        result.scalar_one_or_none.return_value = None
                    return result

                session.execute.side_effect = lambda *args, **kwargs: get_result()
                yield session

            mock_session.return_value = mock_gen()

            await cmd_start(message)

            # Should have sent an error message
            message.answer.assert_called()
            call_args = message.answer.call_args

            # Check that error message contains agent not found text
            error_text = get_text("error_agent_not_found", "ru")
            assert error_text in call_args[0][0]

    @pytest.mark.asyncio
    async def test_invalid_deep_link_format_no_crash(self):
        """Test that invalid deep link format doesn't crash."""
        message = AsyncMock()
        message.text = "/start invalid_format_xyz"  # Invalid format
        message.from_user = MagicMock()
        message.from_user.id = 987654321
        message.from_user.language_code = "en"
        message.from_user.username = "otheruser"
        message.from_user.first_name = "Other"
        message.from_user.last_name = None

        # Mock database session
        with patch('app.bot.handlers.get_async_session') as mock_session:
            async def mock_gen():
                session = AsyncMock()
                user_mock = MagicMock()
                user_mock.preferred_language = "en"
                user_mock.current_agent_id = None

                result = MagicMock()
                result.scalar_one_or_none.return_value = user_mock
                session.execute.return_value = result
                yield session

            mock_session.return_value = mock_gen()

            # Should not raise exception
            await cmd_start(message)

            # Should have sent a message (welcome, not error)
            message.answer.assert_called()


class TestErrorMessages:
    """Test that error messages exist in localization."""

    def test_error_agent_not_found_ru(self):
        """Test Russian agent not found error exists."""
        text = get_text("error_agent_not_found", "ru")
        assert text != "error_agent_not_found"
        assert len(text) > 0

    def test_error_agent_not_found_en(self):
        """Test English agent not found error exists."""
        text = get_text("error_agent_not_found", "en")
        assert text != "error_agent_not_found"
        assert "not found" in text.lower() or "Agent" in text

    def test_error_agent_inactive_ru(self):
        """Test Russian agent inactive error exists."""
        text = get_text("error_agent_inactive", "ru")
        assert text != "error_agent_inactive"
        assert len(text) > 0

    def test_error_agent_inactive_en(self):
        """Test English agent inactive error exists."""
        text = get_text("error_agent_inactive", "en")
        assert text != "error_agent_inactive"
        assert "unavailable" in text.lower() or "inactive" in text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
