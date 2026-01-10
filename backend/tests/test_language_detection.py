"""
Test preferred language detection from Telegram.

Tests that new users get their preferred_language set based on
Telegram's language_code.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.localization import get_user_language, get_text


class TestLanguageDetection:
    """Test get_user_language function."""

    def test_russian_language_code(self):
        """Test Russian language code returns 'ru'."""
        assert get_user_language("ru") == "ru"

    def test_belarusian_language_code(self):
        """Test Belarusian returns Russian (related language)."""
        assert get_user_language("be") == "ru"

    def test_ukrainian_language_code(self):
        """Test Ukrainian returns Russian (related language)."""
        assert get_user_language("uk") == "ru"

    def test_kazakh_language_code(self):
        """Test Kazakh returns Russian (related language)."""
        assert get_user_language("kk") == "ru"

    def test_kyrgyz_language_code(self):
        """Test Kyrgyz returns Russian (related language)."""
        assert get_user_language("ky") == "ru"

    def test_tajik_language_code(self):
        """Test Tajik returns Russian (related language)."""
        assert get_user_language("tg") == "ru"

    def test_uzbek_language_code(self):
        """Test Uzbek returns Russian (related language)."""
        assert get_user_language("uz") == "ru"

    def test_english_language_code(self):
        """Test English returns 'en'."""
        assert get_user_language("en") == "en"

    def test_german_language_code(self):
        """Test German returns 'en' (non-Russian)."""
        assert get_user_language("de") == "en"

    def test_french_language_code(self):
        """Test French returns 'en' (non-Russian)."""
        assert get_user_language("fr") == "en"

    def test_spanish_language_code(self):
        """Test Spanish returns 'en' (non-Russian)."""
        assert get_user_language("es") == "en"

    def test_chinese_language_code(self):
        """Test Chinese returns 'en' (non-Russian)."""
        assert get_user_language("zh") == "en"

    def test_none_language_code_defaults_to_russian(self):
        """Test None defaults to Russian."""
        assert get_user_language(None) == "ru"

    def test_uppercase_language_code(self):
        """Test uppercase language code is handled."""
        assert get_user_language("RU") == "ru"
        assert get_user_language("EN") == "en"

    def test_mixed_case_language_code(self):
        """Test mixed case language code is handled."""
        assert get_user_language("Ru") == "ru"
        assert get_user_language("En") == "en"


class TestUserCreationWithLanguage:
    """Test that user creation sets preferred_language from Telegram."""

    @pytest.mark.asyncio
    async def test_new_user_gets_russian_language(self):
        """Test new user with Russian Telegram gets 'ru' preferred_language."""
        from app.bot.handlers import get_or_create_user

        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456789
        message.from_user.username = "russianuser"
        message.from_user.first_name = "Ivan"
        message.from_user.last_name = "Petrov"
        message.from_user.language_code = "ru"  # Russian Telegram

        mock_session = AsyncMock()
        # No existing user found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Capture the created user
        created_user = None
        def capture_add(user):
            nonlocal created_user
            created_user = user

        mock_session.add = capture_add

        with patch('app.bot.handlers.User') as MockUser:
            mock_user_instance = MagicMock()
            MockUser.return_value = mock_user_instance

            await get_or_create_user(mock_session, message)

            # Verify User was created with Russian language
            MockUser.assert_called_once()
            call_kwargs = MockUser.call_args[1]
            assert call_kwargs['preferred_language'] == 'ru'
            assert call_kwargs['telegram_language_code'] == 'ru'

    @pytest.mark.asyncio
    async def test_new_user_gets_english_language(self):
        """Test new user with English Telegram gets 'en' preferred_language."""
        from app.bot.handlers import get_or_create_user

        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 987654321
        message.from_user.username = "englishuser"
        message.from_user.first_name = "John"
        message.from_user.last_name = "Smith"
        message.from_user.language_code = "en"  # English Telegram

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch('app.bot.handlers.User') as MockUser:
            mock_user_instance = MagicMock()
            MockUser.return_value = mock_user_instance

            await get_or_create_user(mock_session, message)

            MockUser.assert_called_once()
            call_kwargs = MockUser.call_args[1]
            assert call_kwargs['preferred_language'] == 'en'
            assert call_kwargs['telegram_language_code'] == 'en'


class TestLanguageInMessages:
    """Test that messages use user's preferred language."""

    def test_russian_welcome_message(self):
        """Test Russian welcome message."""
        text = get_text("welcome", "ru")
        assert "Добро пожаловать" in text or "TG-Ticket-Agent" in text

    def test_english_welcome_message(self):
        """Test English welcome message."""
        text = get_text("welcome", "en")
        assert "Welcome" in text

    def test_russian_help_text(self):
        """Test Russian help text."""
        text = get_text("help_text", "ru")
        assert "Помощь" in text

    def test_english_help_text(self):
        """Test English help text."""
        text = get_text("help_text", "en")
        assert "Help" in text

    def test_russian_no_tickets(self):
        """Test Russian no tickets message."""
        text = get_text("no_tickets", "ru")
        assert text != "no_tickets"
        assert len(text) > 0

    def test_english_no_tickets(self):
        """Test English no tickets message."""
        text = get_text("no_tickets", "en")
        assert text != "no_tickets"
        assert "ticket" in text.lower()


class TestUserModelLanguageField:
    """Test User model has language fields."""

    def test_user_has_preferred_language(self):
        """Test User model has preferred_language field."""
        from app.models import User
        assert hasattr(User, 'preferred_language')

    def test_user_has_telegram_language_code(self):
        """Test User model has telegram_language_code field."""
        from app.models import User
        assert hasattr(User, 'telegram_language_code')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
