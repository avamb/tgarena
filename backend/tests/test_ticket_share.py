"""
Test ticket share functionality.

Tests for sharing tickets via Telegram.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.localization import get_text


class TestShareButtonExists:
    """Test share button is present on ticket messages."""

    def test_share_button_localization_ru(self):
        """Test share button text exists in Russian."""
        text = get_text("btn_share_ticket", "ru")

        assert len(text) > 0
        assert "Поделиться" in text or "📤" in text

    def test_share_button_localization_en(self):
        """Test share button text exists in English."""
        text = get_text("btn_share_ticket", "en")

        assert len(text) > 0
        assert "Share" in text or "📤" in text


class TestShareButtonImplementation:
    """Test share button implementation in ticket delivery."""

    @pytest.mark.asyncio
    async def test_ticket_delivery_has_share_button(self):
        """Test ticket delivery includes share button."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        source = inspect.getsource(process_ticket_delivery_job)

        # Verify share button is included
        assert "share_keyboard" in source or "InlineKeyboardButton" in source
        assert "switch_inline_query" in source or "Поделиться" in source

    @pytest.mark.asyncio
    async def test_share_button_uses_inline_keyboard(self):
        """Test share button uses InlineKeyboardMarkup."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        source = inspect.getsource(process_ticket_delivery_job)

        # Verify InlineKeyboardMarkup is used
        assert "InlineKeyboardMarkup" in source
        assert "InlineKeyboardButton" in source

    @pytest.mark.asyncio
    async def test_share_keyboard_attached_to_photo(self):
        """Test share keyboard is attached to photo messages."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        source = inspect.getsource(process_ticket_delivery_job)

        # Verify reply_markup is included in send_photo
        assert "reply_markup=share_keyboard" in source or "reply_markup=" in source


class TestTelegramForwardFunctionality:
    """Test that Telegram's native forward works with ticket messages."""

    def test_ticket_message_format_is_forwardable(self):
        """Test ticket message format allows forwarding."""
        # All Telegram messages are forwardable by default
        # This test verifies the ticket format is compatible
        from app.bot.localization import get_text

        ticket_text = get_text(
            "ticket_info", "ru",
            event_name="Concert",
            date="01.01.2026",
            venue="Arena",
            sector="VIP",
            row="A",
            seat="10",
            price=5000
        )

        # Verify ticket contains all important info
        assert "Concert" in ticket_text
        assert "01.01.2026" in ticket_text
        assert "Arena" in ticket_text
        assert "VIP" in ticket_text
        assert "A" in ticket_text
        assert "10" in ticket_text
        assert "5000" in ticket_text

    def test_ticket_uses_html_parse_mode(self):
        """Test ticket uses HTML parse mode for proper formatting."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        source = inspect.getsource(process_ticket_delivery_job)

        # Verify HTML parse mode is used
        assert 'parse_mode="HTML"' in source


class TestSwitchInlineQuery:
    """Test switch_inline_query for sharing."""

    @pytest.mark.asyncio
    async def test_switch_inline_query_format(self):
        """Test switch_inline_query uses ticket ID."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        source = inspect.getsource(process_ticket_delivery_job)

        # Verify switch_inline_query includes ticket identifier
        assert "switch_inline_query" in source
        assert "ticket_" in source or "ticket.id" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
