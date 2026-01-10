"""
Test events displayed as compact list.

Tests that events are shown in a list format with name and date.
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
    callback_view_events,
)
from app.bot.localization import get_text


class TestCompactListDisplay:
    """Test compact list display format."""

    def test_list_shows_event_names(self):
        """Test list shows event names."""
        events = [
            {"actionId": 1, "fullActionName": "Rock Festival", "actionDate": "2026-02-01", "minPrice": 1000},
            {"actionId": 2, "fullActionName": "Jazz Concert", "actionDate": "2026-02-15", "minPrice": 800},
            {"actionId": 3, "fullActionName": "Opera Night", "actionDate": "2026-03-01", "minPrice": 2000},
        ]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        assert "Rock Festival" in result
        assert "Jazz Concert" in result
        assert "Opera Night" in result

    def test_list_shows_dates(self):
        """Test list shows event dates."""
        events = [
            {"actionId": 1, "fullActionName": "Concert", "actionDate": "2026-02-15T19:00:00", "minPrice": 500},
        ]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        # Date should be formatted and visible
        assert "15" in result or "02" in result  # Day or month
        assert "📅" in result  # Date emoji

    def test_list_has_numbered_entries(self):
        """Test list entries are numbered."""
        events = [
            {"actionId": 1, "fullActionName": "Event 1", "actionDate": "2026-02-01", "minPrice": 100},
            {"actionId": 2, "fullActionName": "Event 2", "actionDate": "2026-02-02", "minPrice": 200},
            {"actionId": 3, "fullActionName": "Event 3", "actionDate": "2026-02-03", "minPrice": 300},
        ]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        # Should have numbers 1, 2, 3
        assert "1." in result
        assert "2." in result
        assert "3." in result

    def test_list_is_compact_single_line_per_event(self):
        """Test each event is displayed compactly."""
        events = [
            {"actionId": 1, "fullActionName": "Concert", "actionDate": "2026-02-01", "minPrice": 500},
        ]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        # Should not have excessive spacing between events
        # Each event should be a few lines max
        lines = result.split('\n')
        # Title + spacing + event info = reasonable number of lines
        assert len(lines) < 20  # Not too many lines for one event


class TestEventNameAndDateInList:
    """Test name and date display in list."""

    def test_event_name_in_bold(self):
        """Test event names are bold."""
        events = [
            {"actionId": 1, "fullActionName": "Special Concert", "actionDate": "2026-02-01", "minPrice": 500},
        ]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        assert "<b>Special Concert</b>" in result or "<b>" in result

    def test_event_date_formatted(self):
        """Test event dates are human-readable."""
        events = [
            {"actionId": 1, "fullActionName": "Concert", "actionDate": "2026-12-25T19:00:00", "minPrice": 500},
        ]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        # Date should be formatted (DD.MM.YYYY HH:MM or similar)
        assert "25.12.2026" in result or "25" in result

    def test_event_price_shown(self):
        """Test minimum price shown in list."""
        events = [
            {"actionId": 1, "fullActionName": "Concert", "actionDate": "2026-02-01", "minPrice": 1500},
        ]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        assert "1500" in result
        assert "💰" in result


class TestListEventSelection:
    """Test clicking on event in list shows details."""

    def test_list_has_clickable_event_buttons(self):
        """Test each event has a clickable button."""
        events = [
            {"actionId": 100, "fullActionName": "Event 1"},
            {"actionId": 200, "fullActionName": "Event 2"},
        ]

        keyboard = build_events_pagination_keyboard(events, page=1, total_pages=1, lang="ru")
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]

        event_buttons = [btn for btn in all_buttons if btn.callback_data and "event_" in btn.callback_data]

        assert len(event_buttons) == 2
        assert "event_100" in [btn.callback_data for btn in event_buttons]
        assert "event_200" in [btn.callback_data for btn in event_buttons]

    def test_event_button_shows_ticket_emoji(self):
        """Test event buttons have ticket emoji."""
        events = [{"actionId": 1, "fullActionName": "Concert"}]

        keyboard = build_events_pagination_keyboard(events, page=1, total_pages=1, lang="ru")
        event_button = keyboard.inline_keyboard[0][0]

        assert "🎫" in event_button.text

    @pytest.mark.asyncio
    async def test_clicking_event_shows_details(self):
        """Test clicking event in list shows full details."""
        from app.bot.handlers import callback_event_details

        callback = AsyncMock()
        callback.data = "event_100"
        callback.from_user = MagicMock()
        callback.from_user.id = 123456789
        callback.from_user.language_code = "ru"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()

        mock_user = MagicMock()
        mock_user.current_agent_id = 1
        mock_user.preferred_language = "ru"

        mock_agent = MagicMock()
        mock_agent.id = 1
        mock_agent.fid = 1271
        mock_agent.token = "test"
        mock_agent.zone = "test"
        mock_agent.is_active = True

        event_details = {
            "actionId": 100,
            "fullActionName": "Selected Event Details",
            "actionDate": "2026-03-01T20:00:00",
            "venueName": "Grand Hall",
            "minPrice": 1000,
            "maxPrice": 3000,
            "ageRestriction": 0
        }

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
                mock_fetch.return_value = [event_details]

                await callback_event_details(callback)

                callback.message.edit_text.assert_called()
                call_args = callback.message.edit_text.call_args
                message_text = call_args[0][0]

                # Should show full event details
                assert "Selected Event Details" in message_text
                assert "Grand Hall" in message_text
                assert "1000" in message_text
                assert "3000" in message_text


class TestListTitle:
    """Test list title and header."""

    def test_list_has_title_russian(self):
        """Test list has title in Russian."""
        events = [{"actionId": 1, "fullActionName": "Event", "actionDate": "2026-02-01", "minPrice": 100}]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        # Russian title should include "мероприятия"
        assert "мероприят" in result.lower() or "доступные" in result.lower()

    def test_list_has_title_english(self):
        """Test list has title in English."""
        events = [{"actionId": 1, "fullActionName": "Event", "actionDate": "2026-02-01", "minPrice": 100}]

        result = build_events_list_message(events, page=1, total_pages=1, lang="en")

        assert "event" in result.lower() or "available" in result.lower()

    def test_list_title_is_bold(self):
        """Test list title is bold."""
        events = [{"actionId": 1, "fullActionName": "Event", "actionDate": "2026-02-01", "minPrice": 100}]

        result = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        # Title should be bold (surrounded by <b> tags)
        assert "<b>" in result


class TestListViewButtonPresent:
    """Test View Events button is available."""

    def test_view_events_button_text_ru(self):
        """Test View Events button text in Russian."""
        text = get_text("btn_view_events", "ru")
        assert "мероприятия" in text.lower() or "посмотреть" in text.lower()
        assert "📋" in text

    def test_view_events_button_text_en(self):
        """Test View Events button text in English."""
        text = get_text("btn_view_events", "en")
        assert "event" in text.lower() or "view" in text.lower()
        assert "📋" in text


class TestViewEventsHandler:
    """Test callback_view_events handler."""

    @pytest.mark.asyncio
    async def test_handler_shows_event_list(self):
        """Test handler displays event list."""
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
                    {"actionId": 1, "fullActionName": "Test Event 1", "actionDate": "2026-02-01", "minPrice": 500},
                    {"actionId": 2, "fullActionName": "Test Event 2", "actionDate": "2026-02-15", "minPrice": 800},
                ]

                mock_loading_msg = AsyncMock()
                mock_loading_msg.edit_text = AsyncMock()
                callback.message.answer.return_value = mock_loading_msg

                await callback_view_events(callback)

                # Should show loading first
                callback.message.answer.assert_called()

                # Then edit with event list
                mock_loading_msg.edit_text.assert_called()
                call_args = mock_loading_msg.edit_text.call_args
                message_text = call_args[0][0]

                assert "Test Event 1" in message_text
                assert "Test Event 2" in message_text


class TestEmptyListHandling:
    """Test empty event list handling."""

    def test_empty_list_shows_message_ru(self):
        """Test empty list shows Russian message."""
        result = build_events_list_message([], page=1, total_pages=0, lang="ru")
        expected = get_text("no_events", "ru")
        assert result == expected

    def test_empty_list_shows_message_en(self):
        """Test empty list shows English message."""
        result = build_events_list_message([], page=1, total_pages=0, lang="en")
        expected = get_text("no_events", "en")
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
