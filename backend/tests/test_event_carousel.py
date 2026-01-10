"""
Test bot displays event carousel.

Tests that events are displayed as a paginated list with selection buttons.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.handlers import (
    build_events_list_message,
    build_events_pagination_keyboard,
    build_event_details_message,
    build_event_details_keyboard,
)
from app.bot.localization import get_text


class TestEventListDisplay:
    """Test event list (carousel) display."""

    def test_events_list_shows_event_name(self):
        """Test event list shows event names."""
        events = [
            {"actionId": 1, "fullActionName": "Rock Concert", "actionDate": "2026-02-01T19:00:00", "minPrice": 500},
            {"actionId": 2, "fullActionName": "Jazz Night", "actionDate": "2026-02-02T20:00:00", "minPrice": 800},
        ]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        assert "Rock Concert" in result
        assert "Jazz Night" in result

    def test_events_list_shows_dates(self):
        """Test event list shows event dates."""
        events = [
            {"actionId": 1, "fullActionName": "Concert", "actionDate": "2026-03-15T19:00:00", "minPrice": 500},
        ]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        # Date should be formatted
        assert "15" in result or "2026" in result

    def test_events_list_shows_prices(self):
        """Test event list shows minimum prices."""
        events = [
            {"actionId": 1, "fullActionName": "Concert", "actionDate": "2026-02-01", "minPrice": 1500},
        ]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        assert "1500" in result
        assert "₽" in result

    def test_events_list_shows_page_info(self):
        """Test event list shows current page."""
        events = [
            {"actionId": 1, "fullActionName": "Concert", "actionDate": "2026-02-01", "minPrice": 500},
        ]

        result_ru = build_events_list_message(events, page=2, total_pages=5, lang="ru")
        result_en = build_events_list_message(events, page=2, total_pages=5, lang="en")

        assert "2" in result_ru and "5" in result_ru
        assert "2" in result_en and "5" in result_en

    def test_events_list_truncates_long_names(self):
        """Test event list truncates very long event names."""
        events = [
            {"actionId": 1, "fullActionName": "A" * 100, "actionDate": "2026-02-01", "minPrice": 500},
        ]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        # Name should be truncated with ...
        assert "..." in result
        assert "A" * 100 not in result


class TestEventPaginationKeyboard:
    """Test event pagination keyboard."""

    def test_keyboard_has_event_buttons(self):
        """Test keyboard has button for each event."""
        events = [
            {"actionId": 100, "fullActionName": "Event 1"},
            {"actionId": 200, "fullActionName": "Event 2"},
        ]

        keyboard = build_events_pagination_keyboard(events, page=1, total_pages=1, lang="ru")
        buttons = keyboard.inline_keyboard

        # Find event buttons (excluding pagination)
        event_buttons = [btn for row in buttons for btn in row if "event_" in btn.callback_data]

        assert len(event_buttons) == 2
        assert "event_100" in event_buttons[0].callback_data
        assert "event_200" in event_buttons[1].callback_data

    def test_keyboard_has_next_button_on_first_page(self):
        """Test Next button present on first page with more pages."""
        events = [{"actionId": 1, "fullActionName": "Event"}]

        keyboard = build_events_pagination_keyboard(events, page=1, total_pages=3, lang="ru")

        # Flatten buttons
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        callback_data_list = [btn.callback_data for btn in all_buttons]

        assert any("events_page_2" in cd for cd in callback_data_list)

    def test_keyboard_has_prev_button_on_later_pages(self):
        """Test Previous button present on page 2+."""
        events = [{"actionId": 1, "fullActionName": "Event"}]

        keyboard = build_events_pagination_keyboard(events, page=2, total_pages=3, lang="ru")

        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        callback_data_list = [btn.callback_data for btn in all_buttons]

        assert any("events_page_1" in cd for cd in callback_data_list)

    def test_keyboard_shows_page_indicator(self):
        """Test keyboard shows page indicator."""
        events = [{"actionId": 1, "fullActionName": "Event"}]

        keyboard = build_events_pagination_keyboard(events, page=3, total_pages=10, lang="ru")

        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        button_texts = [btn.text for btn in all_buttons]

        # Page indicator like "3/10"
        assert any("3" in text and "10" in text for text in button_texts)

    def test_event_button_shows_emoji(self):
        """Test event buttons have ticket emoji."""
        events = [{"actionId": 1, "fullActionName": "Concert"}]

        keyboard = build_events_pagination_keyboard(events, page=1, total_pages=1, lang="ru")
        first_button = keyboard.inline_keyboard[0][0]

        assert "🎫" in first_button.text


class TestEventDetailsDisplay:
    """Test event details view."""

    def test_details_shows_event_name(self):
        """Test event details shows event name in bold."""
        event = {
            "fullActionName": "Amazing Concert",
            "actionDate": "2026-02-01T19:00:00",
            "venueName": "Stadium",
            "minPrice": 1000,
            "maxPrice": 5000,
            "ageRestriction": 0
        }

        result = build_event_details_message(event, "ru")

        assert "Amazing Concert" in result
        assert "<b>" in result  # Bold formatting

    def test_details_shows_venue(self):
        """Test event details shows venue."""
        event = {
            "fullActionName": "Concert",
            "actionDate": "2026-02-01T19:00:00",
            "venueName": "Central Stadium",
            "minPrice": 500,
            "maxPrice": 1000,
            "ageRestriction": 0
        }

        result = build_event_details_message(event, "ru")

        assert "Central Stadium" in result
        assert "📍" in result  # Venue emoji

    def test_details_shows_price_range(self):
        """Test event details shows min-max price range."""
        event = {
            "fullActionName": "Concert",
            "actionDate": "2026-02-01T19:00:00",
            "venueName": "Stadium",
            "minPrice": 1000,
            "maxPrice": 5000,
            "ageRestriction": 0
        }

        result = build_event_details_message(event, "ru")

        assert "1000" in result
        assert "5000" in result
        assert "💰" in result  # Price emoji

    def test_details_shows_date(self):
        """Test event details shows formatted date."""
        event = {
            "fullActionName": "Concert",
            "actionDate": "2026-02-15T19:00:00",
            "venueName": "Stadium",
            "minPrice": 500,
            "maxPrice": 1000,
            "ageRestriction": 0
        }

        result = build_event_details_message(event, "ru")

        assert "📅" in result  # Date emoji
        # Date should be formatted somehow

    def test_details_shows_age_restriction_18(self):
        """Test event details shows 18+ age restriction."""
        event = {
            "fullActionName": "Adult Show",
            "actionDate": "2026-02-01T19:00:00",
            "venueName": "Club",
            "minPrice": 2000,
            "maxPrice": 3000,
            "ageRestriction": 18
        }

        result = build_event_details_message(event, "ru")

        assert "18+" in result
        assert "🔞" in result

    def test_details_shows_age_restriction_6(self):
        """Test event details shows 6+ age restriction."""
        event = {
            "fullActionName": "Kids Show",
            "actionDate": "2026-02-01T10:00:00",
            "venueName": "Theater",
            "minPrice": 500,
            "maxPrice": 1500,
            "ageRestriction": 6
        }

        result = build_event_details_message(event, "ru")

        assert "6+" in result


class TestEventDetailsKeyboard:
    """Test event details keyboard buttons."""

    def test_keyboard_has_buy_button(self):
        """Test Buy Ticket button is present."""
        keyboard = build_event_details_keyboard(event_id=123, lang="ru")

        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]

        # Find buy button
        buy_buttons = [btn for btn in all_buttons if "buy_123" in btn.callback_data]

        assert len(buy_buttons) == 1
        assert "🛒" in buy_buttons[0].text

    def test_keyboard_has_back_button(self):
        """Test Back to Events button is present."""
        keyboard = build_event_details_keyboard(event_id=123, lang="ru")

        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]

        # Find back button
        back_buttons = [btn for btn in all_buttons if "back_to_events" in btn.callback_data]

        assert len(back_buttons) == 1
        assert "📋" in back_buttons[0].text or "🔙" in back_buttons[0].text


class TestEventCarouselHandler:
    """Test event carousel handler integration."""

    @pytest.mark.asyncio
    async def test_callback_view_events_displays_list(self):
        """Test View Events callback shows event list."""
        from app.bot.handlers import callback_view_events

        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.id = 111222333
        callback.from_user.language_code = "ru"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()

        mock_user = MagicMock()
        mock_user.current_agent_id = 1
        mock_user.preferred_language = "ru"

        mock_agent = MagicMock()
        mock_agent.id = 1
        mock_agent.fid = 1271
        mock_agent.token = "test_token"
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
                    {"actionId": 1, "fullActionName": "Test Concert", "actionDate": "2026-02-01", "minPrice": 1000}
                ]

                mock_loading_msg = AsyncMock()
                mock_loading_msg.edit_text = AsyncMock()
                callback.message.answer.return_value = mock_loading_msg

                await callback_view_events(callback)

                # Verify edit_text was called with event info
                mock_loading_msg.edit_text.assert_called()
                call_args = mock_loading_msg.edit_text.call_args
                message_text = call_args[0][0]

                assert "Test Concert" in message_text

    @pytest.mark.asyncio
    async def test_callback_event_details_shows_details(self):
        """Test event selection shows full details."""
        from app.bot.handlers import callback_event_details

        callback = AsyncMock()
        callback.data = "event_500"
        callback.from_user = MagicMock()
        callback.from_user.id = 444555666
        callback.from_user.language_code = "en"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()

        mock_user = MagicMock()
        mock_user.current_agent_id = 1
        mock_user.preferred_language = "en"

        mock_agent = MagicMock()
        mock_agent.id = 1
        mock_agent.fid = 1271
        mock_agent.token = "test"
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
                    {
                        "actionId": 500,
                        "fullActionName": "Selected Event",
                        "actionDate": "2026-03-01T20:00:00",
                        "venueName": "Test Venue",
                        "minPrice": 2000,
                        "maxPrice": 5000,
                        "ageRestriction": 16
                    }
                ]

                await callback_event_details(callback)

                callback.message.edit_text.assert_called()
                call_args = callback.message.edit_text.call_args
                message_text = call_args[0][0]

                # Verify details shown
                assert "Selected Event" in message_text
                assert "Test Venue" in message_text
                assert "2000" in message_text
                assert "5000" in message_text


class TestLocalizationForCarousel:
    """Test localization strings for event carousel."""

    def test_view_events_button_text_ru(self):
        """Test View Events button text in Russian."""
        text = get_text("btn_view_events", "ru")
        assert "мероприятия" in text.lower()
        assert "📋" in text

    def test_view_events_button_text_en(self):
        """Test View Events button text in English."""
        text = get_text("btn_view_events", "en")
        assert "event" in text.lower()
        assert "📋" in text

    def test_buy_ticket_button_ru(self):
        """Test Buy Ticket button text in Russian."""
        text = get_text("btn_buy_ticket", "ru")
        assert "🛒" in text
        assert "купить" in text.lower() or "билет" in text.lower()

    def test_buy_ticket_button_en(self):
        """Test Buy Ticket button text in English."""
        text = get_text("btn_buy_ticket", "en")
        assert "🛒" in text
        assert "buy" in text.lower()

    def test_no_events_message_exists(self):
        """Test 'no events' message exists."""
        text_ru = get_text("no_events", "ru")
        text_en = get_text("no_events", "en")

        assert len(text_ru) > 0
        assert len(text_en) > 0


class TestEmptyEventsList:
    """Test handling of empty events list."""

    def test_empty_list_shows_no_events_message(self):
        """Test empty event list shows appropriate message."""
        result = build_events_list_message([], page=1, total_pages=0, lang="ru")

        expected = get_text("no_events", "ru")
        assert result == expected

    def test_empty_list_english(self):
        """Test empty event list message in English."""
        result = build_events_list_message([], page=1, total_pages=0, lang="en")

        expected = get_text("no_events", "en")
        assert result == expected


class TestEventCardFormatting:
    """Test event card formatting matches requirements."""

    def test_event_card_has_emoji_date(self):
        """Test event card has date emoji 📅."""
        events = [{"actionId": 1, "fullActionName": "Test", "actionDate": "2026-02-01", "minPrice": 100}]
        result = build_events_list_message(events, 1, 1, "ru")
        assert "📅" in result

    def test_event_card_has_emoji_price(self):
        """Test event card has price emoji 💰."""
        events = [{"actionId": 1, "fullActionName": "Test", "actionDate": "2026-02-01", "minPrice": 100}]
        result = build_events_list_message(events, 1, 1, "ru")
        assert "💰" in result

    def test_event_details_has_emoji_venue(self):
        """Test event details has venue emoji 📍."""
        event = {
            "fullActionName": "Test",
            "actionDate": "2026-02-01",
            "venueName": "Venue",
            "minPrice": 100,
            "maxPrice": 200,
            "ageRestriction": 0
        }
        result = build_event_details_message(event, "ru")
        assert "📍" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
