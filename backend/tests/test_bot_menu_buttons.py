"""
Test bot menu buttons functionality.

Tests that all menu buttons are present and respond correctly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.handlers import (
    get_main_keyboard,
    callback_help,
    callback_my_tickets,
    callback_noop,
)
from app.bot.localization import get_text


class TestMenuButtonsPresent:
    """Test that menu buttons are correctly generated."""

    def test_main_keyboard_without_agent(self):
        """Test main keyboard when no agent is connected."""
        keyboard = get_main_keyboard(lang="ru", has_agent=False)

        # Should have buttons for help and my_tickets
        assert keyboard.inline_keyboard is not None
        assert len(keyboard.inline_keyboard) > 0

        # Get all callback_data from buttons
        callback_data = []
        for row in keyboard.inline_keyboard:
            for btn in row:
                callback_data.append(btn.callback_data)

        # Should have help and my_tickets buttons
        assert "help" in callback_data
        assert "my_tickets" in callback_data

        # Should NOT have view_events without agent
        assert "view_events" not in callback_data

    def test_main_keyboard_with_agent(self):
        """Test main keyboard when agent is connected."""
        keyboard = get_main_keyboard(lang="ru", has_agent=True)

        callback_data = []
        for row in keyboard.inline_keyboard:
            for btn in row:
                callback_data.append(btn.callback_data)

        # Should have all three buttons
        assert "help" in callback_data
        assert "my_tickets" in callback_data
        assert "view_events" in callback_data

    def test_main_keyboard_localized_ru(self):
        """Test Russian button labels."""
        keyboard = get_main_keyboard(lang="ru", has_agent=True)

        # Collect all button texts
        button_texts = []
        for row in keyboard.inline_keyboard:
            for btn in row:
                button_texts.append(btn.text)

        # Check that at least one button has Russian text
        assert any("Помощь" in text for text in button_texts) or any("помощь" in text.lower() for text in button_texts)

    def test_main_keyboard_localized_en(self):
        """Test English button labels."""
        keyboard = get_main_keyboard(lang="en", has_agent=True)

        button_texts = []
        for row in keyboard.inline_keyboard:
            for btn in row:
                button_texts.append(btn.text)

        # Check that at least one button has English text
        assert any("Help" in text for text in button_texts)


class TestMenuButtonCallbacks:
    """Test that menu button callbacks work correctly."""

    @pytest.mark.asyncio
    async def test_help_callback_answers(self):
        """Test that help callback sends a response."""
        # Create mock callback
        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.language_code = "ru"
        callback.message = AsyncMock()

        await callback_help(callback)

        # Should have answered the callback
        callback.answer.assert_called_once()

        # Should have sent help text
        callback.message.answer.assert_called_once()
        args = callback.message.answer.call_args
        assert "Помощь" in args[0][0] or "help" in args[0][0].lower()

    @pytest.mark.asyncio
    async def test_my_tickets_callback_answers(self):
        """Test that my_tickets callback sends a response."""
        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.language_code = "en"
        callback.message = AsyncMock()

        await callback_my_tickets(callback)

        callback.answer.assert_called_once()
        callback.message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_noop_callback_only_answers(self):
        """Test that noop callback only answers (no message)."""
        callback = AsyncMock()

        await callback_noop(callback)

        callback.answer.assert_called_once()


class TestLocalizationStrings:
    """Test that all required localization strings exist."""

    def test_button_texts_exist_ru(self):
        """Test Russian button texts exist."""
        assert get_text("btn_view_events", "ru") != "btn_view_events"
        assert get_text("btn_my_tickets", "ru") != "btn_my_tickets"
        assert get_text("btn_help", "ru") != "btn_help"
        assert get_text("btn_back", "ru") != "btn_back"

    def test_button_texts_exist_en(self):
        """Test English button texts exist."""
        assert get_text("btn_view_events", "en") != "btn_view_events"
        assert get_text("btn_my_tickets", "en") != "btn_my_tickets"
        assert get_text("btn_help", "en") != "btn_help"
        assert get_text("btn_back", "en") != "btn_back"

    def test_help_text_exists(self):
        """Test help text exists in both languages."""
        help_ru = get_text("help_text", "ru")
        help_en = get_text("help_text", "en")

        assert help_ru != "help_text"
        assert help_en != "help_text"
        assert len(help_ru) > 50  # Should be a substantial help message
        assert len(help_en) > 50

    def test_ticket_related_texts_exist(self):
        """Test ticket-related texts exist."""
        assert get_text("no_tickets", "ru") != "no_tickets"
        assert get_text("no_tickets", "en") != "no_tickets"

    def test_error_messages_exist(self):
        """Test error messages exist."""
        assert get_text("error_no_agent", "ru") != "error_no_agent"
        assert get_text("error_no_agent", "en") != "error_no_agent"
        assert get_text("error_general", "ru") != "error_general"
        assert get_text("error_general", "en") != "error_general"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
