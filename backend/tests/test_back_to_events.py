"""
Test back navigation from event details to events list.

Tests the event details view and back navigation handlers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.handlers import (
    build_event_details_message,
    build_event_details_keyboard,
    callback_event_details,
    callback_back_to_events,
)
from app.bot.localization import get_text


class TestEventDetailsMessage:
    """Test event details message building."""

    def test_build_event_details_message_basic(self):
        """Test building event details message with all fields."""
        event = {
            "fullActionName": "Concert 2025",
            "actionDate": "2025-12-25T19:00:00",
            "venueName": "Big Arena",
            "minPrice": 1000,
            "maxPrice": 5000,
            "ageRestriction": 0,
        }

        message = build_event_details_message(event, "ru")

        assert "Concert 2025" in message
        assert "25.12.2025" in message
        assert "Big Arena" in message
        assert "1000" in message
        assert "5000" in message

    def test_build_event_details_message_fallback_name(self):
        """Test using actionName when fullActionName is missing."""
        event = {
            "actionName": "Simple Event",
            "actionDate": "2025-06-15T20:00:00",
            "cityName": "Moscow",
            "minPrice": 500,
        }

        message = build_event_details_message(event, "en")

        assert "Simple Event" in message
        assert "Moscow" in message

    def test_build_event_details_message_with_age_restriction(self):
        """Test event with age restriction."""
        event = {
            "fullActionName": "Adult Show",
            "actionDate": "2025-07-01T21:00:00",
            "venueName": "Club",
            "minPrice": 2000,
            "maxPrice": 2000,
            "ageRestriction": 18,
        }

        message = build_event_details_message(event, "ru")

        assert "Adult Show" in message
        assert "18+" in message

    def test_build_event_details_message_en(self):
        """Test English locale."""
        event = {
            "fullActionName": "English Event",
            "actionDate": "2025-08-20T18:00:00",
            "venueName": "Hall",
            "minPrice": 100,
            "maxPrice": 200,
            "ageRestriction": 0,
        }

        message = build_event_details_message(event, "en")

        assert "English Event" in message
        assert "Date:" in message  # English text

    def test_build_event_details_message_uses_action_event_venue(self):
        """Test venue fallback from actionEventList when root venue is absent."""
        event = {
            "fullActionName": "Session Venue Event",
            "firstEventDate": "20.08.2025",
            "actionEventList": [
                {
                    "venueName": "Session Arena",
                    "cityName": "Paris",
                    "currency": "EUR",
                }
            ],
            "minPrice": 100,
            "maxPrice": 200,
        }

        message = build_event_details_message(event, "en")

        assert "Session Arena" in message


class TestEventDetailsKeyboard:
    """Test event details keyboard building."""

    def test_keyboard_has_buy_button(self):
        """Test that keyboard has buy ticket button."""
        keyboard = build_event_details_keyboard(event_id=123, lang="ru")

        # Find buy button
        buy_buttons = []
        for row in keyboard.inline_keyboard:
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("buy_"):
                    buy_buttons.append(btn)

        assert len(buy_buttons) == 1
        assert buy_buttons[0].callback_data == "buy_123"
        assert "Купить" in buy_buttons[0].text or "билет" in buy_buttons[0].text.lower()

    def test_keyboard_has_back_to_events_button(self):
        """Test that keyboard has back to events button."""
        keyboard = build_event_details_keyboard(event_id=456, lang="ru")

        # Find back button
        back_buttons = []
        for row in keyboard.inline_keyboard:
            for btn in row:
                if btn.callback_data == "back_to_events":
                    back_buttons.append(btn)

        assert len(back_buttons) == 1

    def test_keyboard_english_locale(self):
        """Test keyboard with English locale."""
        keyboard = build_event_details_keyboard(event_id=789, lang="en")

        # Find back button
        back_button = None
        for row in keyboard.inline_keyboard:
            for btn in row:
                if btn.callback_data == "back_to_events":
                    back_button = btn

        assert back_button is not None
        assert "Back" in back_button.text or "Events" in back_button.text


class TestEventDetailsCallback:
    """Test event details callback handler."""

    @pytest.mark.asyncio
    async def test_event_details_extracts_event_id(self):
        """Test that event ID is correctly extracted from callback."""
        callback = AsyncMock()
        callback.data = "event_12345"
        callback.from_user = MagicMock()
        callback.from_user.language_code = "ru"
        callback.from_user.id = 111222333
        callback.message = AsyncMock()

        # Mock database session
        with patch('app.bot.handlers.get_async_session') as mock_session:
            # Create a proper async generator mock
            async def mock_gen():
                session = AsyncMock()
                result = MagicMock()
                result.scalar_one_or_none.return_value = None  # No user found
                session.execute.return_value = result
                yield session

            mock_session.return_value = mock_gen()

            await callback_event_details(callback)

            # Should have answered the callback
            callback.answer.assert_called()

    @pytest.mark.asyncio
    async def test_event_details_invalid_id_format(self):
        """Test handling of invalid event ID format."""
        callback = AsyncMock()
        callback.data = "event_invalid"
        callback.from_user = MagicMock()
        callback.from_user.language_code = "en"
        callback.message = AsyncMock()

        await callback_event_details(callback)

        # Should answer with error
        callback.answer.assert_called()


class TestBackToEventsCallback:
    """Test back to events callback handler."""

    @pytest.mark.asyncio
    async def test_back_to_events_answers_callback(self):
        """Test that back to events callback answers."""
        callback = AsyncMock()
        callback.data = "back_to_events"
        callback.from_user = MagicMock()
        callback.from_user.language_code = "ru"
        callback.from_user.id = 444555666
        callback.message = AsyncMock()

        # Mock database session
        with patch('app.bot.handlers.get_async_session') as mock_session:
            async def mock_gen():
                session = AsyncMock()
                result = MagicMock()
                result.scalar_one_or_none.return_value = None
                session.execute.return_value = result
                yield session

            mock_session.return_value = mock_gen()

            await callback_back_to_events(callback)

            callback.answer.assert_called_once()


class TestLocalizationStrings:
    """Test that required localization strings exist."""

    def test_back_to_events_button_text_ru(self):
        """Test Russian back to events button text."""
        text = get_text("btn_back_to_events", "ru")
        assert text != "btn_back_to_events"
        assert len(text) > 0

    def test_back_to_events_button_text_en(self):
        """Test English back to events button text."""
        text = get_text("btn_back_to_events", "en")
        assert text != "btn_back_to_events"
        assert "Back" in text or "Events" in text

    def test_error_event_not_found_ru(self):
        """Test Russian event not found error."""
        text = get_text("error_event_not_found", "ru")
        assert text != "error_event_not_found"

    def test_error_event_not_found_en(self):
        """Test English event not found error."""
        text = get_text("error_event_not_found", "en")
        assert text != "error_event_not_found"
        assert "not found" in text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
