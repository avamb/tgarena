"""
Test English language fallback.

Tests for English localization for non-Russian users.
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.localization import get_text, get_user_language, TRANSLATIONS


class TestEnglishWelcomeMessage:
    """Test welcome message in English."""

    def test_welcome_message_exists_en(self):
        """Test welcome message exists in English."""
        text = get_text("welcome", "en")
        assert len(text) > 0

    def test_welcome_message_in_english(self):
        """Test welcome message contains English text."""
        text = get_text("welcome", "en")
        assert "Welcome" in text or "welcome" in text.lower()

    def test_welcome_with_agent_in_english(self):
        """Test welcome with agent message in English."""
        text = get_text("welcome_with_agent", "en", agent_name="Test Agent")
        assert "Test Agent" in text
        assert "connected" in text.lower() or "agent" in text.lower()


class TestEnglishButtons:
    """Test all buttons in English."""

    def test_view_events_button_en(self):
        """Test view events button in English."""
        text = get_text("btn_view_events", "en")
        assert "Event" in text or "event" in text.lower()

    def test_my_tickets_button_en(self):
        """Test my tickets button in English."""
        text = get_text("btn_my_tickets", "en")
        assert "Ticket" in text or "ticket" in text.lower()

    def test_help_button_en(self):
        """Test help button in English."""
        text = get_text("btn_help", "en")
        assert "Help" in text or "❓" in text

    def test_buy_ticket_button_en(self):
        """Test buy ticket button in English."""
        text = get_text("btn_buy_ticket", "en")
        assert "Buy" in text or "Ticket" in text

    def test_back_button_en(self):
        """Test back button in English."""
        text = get_text("btn_back", "en")
        assert "Back" in text or "🔙" in text

    def test_next_event_button_en(self):
        """Test next event button in English."""
        text = get_text("btn_next_event", "en")
        assert "Next" in text or "➡️" in text

    def test_prev_event_button_en(self):
        """Test previous event button in English."""
        text = get_text("btn_prev_event", "en")
        assert "Previous" in text or "⬅️" in text

    def test_share_button_en(self):
        """Test share button in English."""
        text = get_text("btn_share_ticket", "en")
        assert "Share" in text or "📤" in text


class TestEnglishErrorMessages:
    """Test error messages in English."""

    def test_general_error_en(self):
        """Test general error in English."""
        text = get_text("error_general", "en")
        assert "error" in text.lower() or "try" in text.lower()

    def test_no_agent_error_en(self):
        """Test no agent error in English."""
        text = get_text("error_no_agent", "en")
        assert "agent" in text.lower() or "link" in text.lower()

    def test_agent_not_found_error_en(self):
        """Test agent not found error in English."""
        text = get_text("error_agent_not_found", "en")
        assert "not found" in text.lower() or "Agent" in text

    def test_agent_inactive_error_en(self):
        """Test agent inactive error in English."""
        text = get_text("error_agent_inactive", "en")
        assert "unavailable" in text.lower() or "Agent" in text


class TestEnglishEventMessages:
    """Test event-related messages in English."""

    def test_no_events_message_en(self):
        """Test no events message in English."""
        text = get_text("no_events", "en")
        assert "no events" in text.lower() or "event" in text.lower()

    def test_events_list_title_en(self):
        """Test events list title in English."""
        text = get_text("events_list_title", "en", page=1, total_pages=3)
        assert "Event" in text or "Page" in text

    def test_event_details_format_en(self):
        """Test event details format in English."""
        text = get_text("event_details", "en",
                       name="Concert",
                       date="01.01.2026",
                       venue="Arena",
                       min_price=1000,
                       max_price=5000,
                       age_restriction="",
                       countdown="")
        assert "Concert" in text
        assert "Arena" in text

    def test_loading_events_en(self):
        """Test loading events message in English."""
        text = get_text("loading_events", "en")
        assert "Loading" in text or "⏳" in text


class TestEnglishHelpText:
    """Test help text in English."""

    def test_help_text_en(self):
        """Test help text is in English."""
        text = get_text("help_text", "en")
        assert "ticket" in text.lower()
        assert "buy" in text.lower() or "purchase" in text.lower()


class TestEnglishTicketMessages:
    """Test ticket-related messages in English."""

    def test_no_tickets_en(self):
        """Test no tickets message in English."""
        text = get_text("no_tickets", "en")
        assert "ticket" in text.lower()

    def test_ticket_info_en(self):
        """Test ticket info in English."""
        text = get_text("ticket_info", "en",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Arena",
                       sector="VIP",
                       row="A",
                       seat="10",
                       price=5000)
        assert "Concert" in text
        assert "Row" in text or "Seat" in text


class TestLanguageFallback:
    """Test language fallback to English for non-Russian users."""

    def test_english_language_code(self):
        """Test English language code returns en."""
        assert get_user_language("en") == "en"

    def test_german_returns_english(self):
        """Test German language code returns English."""
        assert get_user_language("de") == "en"

    def test_french_returns_english(self):
        """Test French language code returns English."""
        assert get_user_language("fr") == "en"

    def test_spanish_returns_english(self):
        """Test Spanish language code returns English."""
        assert get_user_language("es") == "en"

    def test_chinese_returns_english(self):
        """Test Chinese language code returns English."""
        assert get_user_language("zh") == "en"

    def test_japanese_returns_english(self):
        """Test Japanese language code returns English."""
        assert get_user_language("ja") == "en"


class TestAllEnglishTranslationsExist:
    """Test that all required English translations exist."""

    def test_all_en_keys_exist(self):
        """Test all English translation keys exist."""
        en_translations = TRANSLATIONS.get("en", {})

        # Required keys
        required_keys = [
            "welcome",
            "welcome_with_agent",
            "btn_view_events",
            "btn_my_tickets",
            "btn_help",
            "btn_buy_ticket",
            "btn_back",
            "no_events",
            "events_list_title",
            "event_details",
            "no_tickets",
            "ticket_info",
            "error_general",
            "help_text",
        ]

        for key in required_keys:
            assert key in en_translations, f"Missing English translation: {key}"
            assert len(en_translations[key]) > 0, f"Empty English translation: {key}"

    def test_en_translations_match_ru_keys(self):
        """Test English translations have same keys as Russian."""
        ru_translations = TRANSLATIONS.get("ru", {})
        en_translations = TRANSLATIONS.get("en", {})

        for key in ru_translations:
            assert key in en_translations, f"Missing English translation for key: {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
