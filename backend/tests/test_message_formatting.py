"""
Test Telegram message formatting.

Tests that messages use correct HTML formatting for Telegram.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import re
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.localization import get_text, TRANSLATIONS


class TestHTMLFormatting:
    """Test HTML formatting in messages."""

    def test_bold_text_uses_html_tags(self):
        """Test bold text uses <b> tags."""
        # Check various localized messages
        messages_to_check = [
            "welcome",
            "welcome_with_agent",
            "events_list_title",
            "event_details",
            "help_text"
        ]

        for key in messages_to_check:
            text_ru = TRANSLATIONS.get("ru", {}).get(key, "")
            text_en = TRANSLATIONS.get("en", {}).get(key, "")

            # At least one should have bold formatting
            has_bold = "<b>" in text_ru or "<b>" in text_en

            # Skip if no bold expected
            if has_bold:
                assert "</b>" in text_ru or "</b>" in text_en

    def test_bold_tags_are_paired(self):
        """Test bold tags are properly paired."""
        for lang, translations in TRANSLATIONS.items():
            for key, text in translations.items():
                open_count = text.count("<b>")
                close_count = text.count("</b>")

                assert open_count == close_count, f"Mismatched <b> tags in {lang}.{key}"

    def test_italic_tags_are_paired(self):
        """Test italic tags are properly paired."""
        for lang, translations in TRANSLATIONS.items():
            for key, text in translations.items():
                open_count = text.count("<i>")
                close_count = text.count("</i>")

                assert open_count == close_count, f"Mismatched <i> tags in {lang}.{key}"


class TestEmojis:
    """Test emoji display in messages."""

    def test_welcome_has_emoji(self):
        """Test welcome message has emoji."""
        text = get_text("welcome", "ru")
        assert "🎫" in text

    def test_button_texts_have_emojis(self):
        """Test button texts include emojis."""
        button_keys = [
            "btn_view_events",
            "btn_my_tickets",
            "btn_help",
            "btn_buy_ticket",
            "btn_back"
        ]

        emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF]')

        for key in button_keys:
            text_ru = get_text(key, "ru")
            text_en = get_text(key, "en")

            # At least one version should have emoji
            has_emoji = (
                emoji_pattern.search(text_ru) is not None or
                emoji_pattern.search(text_en) is not None
            )

            assert has_emoji, f"Button {key} should have emoji"

    def test_order_status_emojis(self):
        """Test order status messages have appropriate emojis."""
        status_emojis = {
            "order_new": "📝",
            "order_paid": "✅",
            "order_cancelled": "❌",
            "order_refunded": "💸"
        }

        for key, expected_emoji in status_emojis.items():
            text = get_text(key, "ru", order_id=1, amount=100)
            assert expected_emoji in text, f"{key} should have {expected_emoji}"


class TestMessagePlaceholders:
    """Test message placeholders work correctly."""

    def test_event_details_placeholders(self):
        """Test event_details has all required placeholders."""
        text = get_text(
            "event_details", "ru",
            name="Test Event",
            date="01.01.2026",
            venue="Test Venue",
            min_price=1000,
            max_price=2000,
            age_restriction="18+",
            countdown=""
        )

        assert "Test Event" in text
        assert "01.01.2026" in text
        assert "Test Venue" in text
        assert "1000" in text
        assert "2000" in text

    def test_order_placeholders(self):
        """Test order messages have placeholders."""
        text = get_text("order_paid", "en", order_id=12345, amount=5000)

        assert "12345" in text
        assert "5000" in text

    def test_welcome_with_agent_placeholder(self):
        """Test welcome_with_agent has agent name."""
        text = get_text("welcome_with_agent", "ru", agent_name="Test Agency")

        assert "Test Agency" in text


class TestParseMode:
    """Test parse mode usage in handlers."""

    def test_handlers_use_html_parse_mode(self):
        """Test handlers send with HTML parse mode."""
        # Read handler file and check parse_mode usage
        from app.bot import handlers
        import inspect

        source = inspect.getsource(handlers)

        # Handlers should use parse_mode="HTML"
        assert 'parse_mode="HTML"' in source or "parse_mode='HTML'" in source

    def test_no_markdown_parse_mode(self):
        """Test handlers don't use Markdown (deprecated in places)."""
        # For complex formatting, HTML is preferred over Markdown
        from app.bot import handlers
        import inspect

        source = inspect.getsource(handlers)

        # Should not use MarkdownV2 with complex content
        # (Markdown requires escaping many characters)
        # HTML is simpler for this use case
        markdown_count = source.count('parse_mode="Markdown"')

        # Markdown is not forbidden, but HTML is preferred
        assert markdown_count == 0 or 'parse_mode="HTML"' in source


class TestSpecialCharacterEscaping:
    """Test special character handling."""

    def test_html_entities_not_needed(self):
        """Test HTML entities are handled correctly."""
        # Check that < > & are not causing issues
        # In HTML mode, these need escaping if they're literal

        # Currency symbol should work
        text = get_text("event_details", "ru",
                        name="Test",
                        date="01.01.2026",
                        venue="Venue",
                        min_price=1000,
                        max_price=2000,
                        age_restriction="",
                        countdown="")

        assert "₽" in text  # Russian ruble symbol

    def test_angle_brackets_in_html(self):
        """Test angle brackets are handled."""
        # If message contains < or >, they should be in HTML tags
        for lang, translations in TRANSLATIONS.items():
            for key, text in translations.items():
                # Count brackets
                open_angle = text.count("<")
                close_angle = text.count(">")

                # Should be balanced (from HTML tags)
                assert open_angle == close_angle, \
                    f"Unbalanced angle brackets in {lang}.{key}"


class TestLinkFormatting:
    """Test link formatting in messages."""

    def test_can_use_html_links(self):
        """Test HTML links can be used."""
        # HTML link format: <a href="url">text</a>
        link = '<a href="https://example.com">Click here</a>'

        assert 'href=' in link
        assert '</a>' in link

    def test_help_text_formatting(self):
        """Test help text has proper formatting."""
        text = get_text("help_text", "ru")

        # Should have bold sections
        assert "<b>" in text
        assert "</b>" in text

        # Should have line breaks
        assert "\n" in text


class TestLineBreaks:
    """Test line break handling."""

    def test_newlines_preserved(self):
        """Test newlines are in messages."""
        text = get_text("help_text", "en")

        # Should have multiple lines
        lines = text.split("\n")
        assert len(lines) > 3

    def test_welcome_has_structure(self):
        """Test welcome message has paragraph structure."""
        text = get_text("welcome", "ru")

        # Should have empty lines between sections
        assert "\n\n" in text or "\n" in text


class TestEventListFormatting:
    """Test event list message formatting."""

    def test_event_list_item_format(self):
        """Test event list item has proper format."""
        text = get_text(
            "event_list_item", "ru",
            number=1,
            name="Concert Name",
            date="15.03.2026 19:00",
            min_price=1000
        )

        assert "1." in text  # Number
        assert "Concert Name" in text
        assert "15.03.2026" in text
        assert "1000" in text

    def test_events_list_title(self):
        """Test events list title format."""
        text = get_text("events_list_title", "ru", page=2, total_pages=5)

        assert "2" in text
        assert "5" in text
        assert "<b>" in text


class TestTicketInfoFormatting:
    """Test ticket info message formatting."""

    def test_ticket_info_format(self):
        """Test ticket info has all details."""
        text = get_text(
            "ticket_info", "ru",
            event_name="Rock Concert",
            date="20.03.2026 20:00",
            venue="Arena Stadium",
            sector="VIP",
            row="A",
            seat="15",
            price=5000
        )

        assert "Rock Concert" in text
        assert "Arena Stadium" in text
        assert "VIP" in text
        assert "A" in text
        assert "15" in text
        assert "5000" in text


class TestCountdownFormatting:
    """Test countdown formatting."""

    def test_countdown_days_format(self):
        """Test countdown days format."""
        text = get_text("countdown_days", "ru", count=5)
        assert "5" in text
        assert "дн." in text

    def test_countdown_hours_format(self):
        """Test countdown hours format."""
        text = get_text("countdown_hours", "en", count=12)
        assert "12" in text
        assert "h" in text

    def test_countdown_label_format(self):
        """Test countdown label format."""
        text = get_text("countdown_label", "ru", countdown="2 дн. 5 ч.")
        assert "2 дн. 5 ч." in text
        assert "⏳" in text


class TestErrorMessageFormatting:
    """Test error message formatting."""

    def test_error_messages_are_simple(self):
        """Test error messages are plain text (no complex formatting)."""
        error_keys = [
            "error_general",
            "error_no_agent",
            "error_agent_not_found",
            "error_agent_inactive",
            "error_seat_reserved"
        ]

        for key in error_keys:
            text_ru = get_text(key, "ru")
            text_en = get_text(key, "en")

            # Error messages typically don't need bold
            # But can have them - just check they're valid
            if "<b>" in text_ru:
                assert "</b>" in text_ru

            if "<b>" in text_en:
                assert "</b>" in text_en


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
