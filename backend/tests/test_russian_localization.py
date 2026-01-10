"""
Test Russian language messages.

Tests for Russian localization throughout the bot.
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.localization import get_text, get_user_language, TRANSLATIONS


class TestRussianWelcomeMessage:
    """Test welcome message in Russian."""

    def test_welcome_message_exists_ru(self):
        """Test welcome message exists in Russian."""
        text = get_text("welcome", "ru")
        assert len(text) > 0

    def test_welcome_message_in_russian(self):
        """Test welcome message contains Russian text."""
        text = get_text("welcome", "ru")
        # Russian text should contain Cyrillic characters
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        assert has_cyrillic

    def test_welcome_with_agent_in_russian(self):
        """Test welcome with agent message in Russian."""
        text = get_text("welcome_with_agent", "ru", agent_name="Тест Агент")
        assert "Тест Агент" in text
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        assert has_cyrillic


class TestRussianButtons:
    """Test all buttons in Russian."""

    def test_view_events_button_ru(self):
        """Test view events button in Russian."""
        text = get_text("btn_view_events", "ru")
        assert "мероприятия" in text.lower() or "событ" in text.lower()

    def test_my_tickets_button_ru(self):
        """Test my tickets button in Russian."""
        text = get_text("btn_my_tickets", "ru")
        assert "билет" in text.lower()

    def test_help_button_ru(self):
        """Test help button in Russian."""
        text = get_text("btn_help", "ru")
        assert "Помощь" in text or "❓" in text

    def test_buy_ticket_button_ru(self):
        """Test buy ticket button in Russian."""
        text = get_text("btn_buy_ticket", "ru")
        assert "Купить" in text or "билет" in text.lower()

    def test_back_button_ru(self):
        """Test back button in Russian."""
        text = get_text("btn_back", "ru")
        assert "Назад" in text or "🔙" in text

    def test_next_event_button_ru(self):
        """Test next event button in Russian."""
        text = get_text("btn_next_event", "ru")
        assert "Следующ" in text or "➡️" in text

    def test_prev_event_button_ru(self):
        """Test previous event button in Russian."""
        text = get_text("btn_prev_event", "ru")
        assert "Предыдущ" in text or "⬅️" in text

    def test_share_button_ru(self):
        """Test share button in Russian."""
        text = get_text("btn_share_ticket", "ru")
        assert "Поделиться" in text or "📤" in text


class TestRussianErrorMessages:
    """Test error messages in Russian."""

    def test_general_error_ru(self):
        """Test general error in Russian."""
        text = get_text("error_general", "ru")
        assert "ошибка" in text.lower() or "попробуйте" in text.lower()

    def test_no_agent_error_ru(self):
        """Test no agent error in Russian."""
        text = get_text("error_no_agent", "ru")
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        assert has_cyrillic

    def test_agent_not_found_error_ru(self):
        """Test agent not found error in Russian."""
        text = get_text("error_agent_not_found", "ru")
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        assert has_cyrillic

    def test_agent_inactive_error_ru(self):
        """Test agent inactive error in Russian."""
        text = get_text("error_agent_inactive", "ru")
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        assert has_cyrillic

    def test_seat_reserved_error_ru(self):
        """Test seat reserved error in Russian."""
        text = get_text("error_seat_reserved", "ru")
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        assert has_cyrillic

    def test_payment_failed_error_ru(self):
        """Test payment failed error in Russian."""
        text = get_text("error_payment_failed", "ru")
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        assert has_cyrillic


class TestRussianEventMessages:
    """Test event-related messages in Russian."""

    def test_no_events_message_ru(self):
        """Test no events message in Russian."""
        text = get_text("no_events", "ru")
        assert "мероприятий" in text.lower()

    def test_events_list_title_ru(self):
        """Test events list title in Russian."""
        text = get_text("events_list_title", "ru", page=1, total_pages=3)
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        assert has_cyrillic

    def test_event_details_format_ru(self):
        """Test event details format in Russian."""
        text = get_text("event_details", "ru",
                       name="Концерт",
                       date="01.01.2026",
                       venue="Арена",
                       min_price=1000,
                       max_price=5000,
                       age_restriction="",
                       countdown="")
        assert "Концерт" in text
        assert "Арена" in text
        assert "1000" in text

    def test_loading_events_ru(self):
        """Test loading events message in Russian."""
        text = get_text("loading_events", "ru")
        assert "Загруж" in text or "⏳" in text


class TestRussianHelpText:
    """Test help text in Russian."""

    def test_help_text_ru(self):
        """Test help text is in Russian."""
        text = get_text("help_text", "ru")
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        assert has_cyrillic
        assert "билет" in text.lower()

    def test_unknown_command_ru(self):
        """Test unknown command message in Russian."""
        text = get_text("unknown_command", "ru")
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        assert has_cyrillic


class TestRussianTicketMessages:
    """Test ticket-related messages in Russian."""

    def test_no_tickets_ru(self):
        """Test no tickets message in Russian."""
        text = get_text("no_tickets", "ru")
        assert "билет" in text.lower()

    def test_ticket_info_ru(self):
        """Test ticket info in Russian."""
        text = get_text("ticket_info", "ru",
                       event_name="Концерт",
                       date="01.01.2026",
                       venue="Арена",
                       sector="VIP",
                       row="A",
                       seat="10",
                       price=5000)
        assert "Концерт" in text
        assert "Ряд" in text or "row" in text.lower()


class TestLanguageDetection:
    """Test language detection for Russian users."""

    def test_russian_language_code(self):
        """Test Russian language code returns ru."""
        assert get_user_language("ru") == "ru"

    def test_belarusian_returns_russian(self):
        """Test Belarusian language code returns Russian."""
        assert get_user_language("be") == "ru"

    def test_ukrainian_returns_russian(self):
        """Test Ukrainian language code returns Russian."""
        assert get_user_language("uk") == "ru"

    def test_kazakh_returns_russian(self):
        """Test Kazakh language code returns Russian."""
        assert get_user_language("kk") == "ru"

    def test_none_returns_russian(self):
        """Test None language code returns Russian (default)."""
        assert get_user_language(None) == "ru"


class TestAllRussianTranslationsExist:
    """Test that all required Russian translations exist."""

    def test_all_ru_keys_exist(self):
        """Test all Russian translation keys exist."""
        ru_translations = TRANSLATIONS.get("ru", {})

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
            assert key in ru_translations, f"Missing Russian translation: {key}"
            assert len(ru_translations[key]) > 0, f"Empty Russian translation: {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
