"""
Test event pagination functionality.

Tests the pagination helper functions in bot handlers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.handlers import (
    EVENTS_PER_PAGE,
    get_page_events,
    build_events_list_message,
    build_events_pagination_keyboard,
    format_event_date,
)


class TestEventPagination:
    """Test event pagination helper functions."""

    def test_events_per_page_constant(self):
        """Verify EVENTS_PER_PAGE is set."""
        assert EVENTS_PER_PAGE == 5

    def test_get_page_events_first_page(self):
        """Test getting first page of events."""
        events = [{"actionId": i, "actionName": f"Event {i}"} for i in range(12)]

        page_events, total_pages = get_page_events(events, page=1)

        assert len(page_events) == 5
        assert total_pages == 3
        assert page_events[0]["actionId"] == 0
        assert page_events[4]["actionId"] == 4

    def test_get_page_events_second_page(self):
        """Test getting second page of events."""
        events = [{"actionId": i, "actionName": f"Event {i}"} for i in range(12)]

        page_events, total_pages = get_page_events(events, page=2)

        assert len(page_events) == 5
        assert total_pages == 3
        assert page_events[0]["actionId"] == 5
        assert page_events[4]["actionId"] == 9

    def test_get_page_events_last_page(self):
        """Test getting last page with fewer events."""
        events = [{"actionId": i, "actionName": f"Event {i}"} for i in range(12)]

        page_events, total_pages = get_page_events(events, page=3)

        assert len(page_events) == 2  # Only 2 events on last page
        assert total_pages == 3
        assert page_events[0]["actionId"] == 10
        assert page_events[1]["actionId"] == 11

    def test_get_page_events_out_of_bounds(self):
        """Test page number beyond total pages."""
        events = [{"actionId": i, "actionName": f"Event {i}"} for i in range(12)]

        # Page 10 is beyond the 3 total pages, should clamp to last page
        page_events, total_pages = get_page_events(events, page=10)

        assert len(page_events) == 2
        assert total_pages == 3

    def test_get_page_events_zero_page(self):
        """Test page 0 returns first page."""
        events = [{"actionId": i, "actionName": f"Event {i}"} for i in range(12)]

        page_events, total_pages = get_page_events(events, page=0)

        assert len(page_events) == 5
        assert page_events[0]["actionId"] == 0

    def test_get_page_events_empty_list(self):
        """Test empty event list."""
        events = []

        page_events, total_pages = get_page_events(events, page=1)

        assert len(page_events) == 0
        assert total_pages == 1

    def test_format_event_date_valid(self):
        """Test formatting valid date."""
        date_str = "2025-12-25T19:00:00"
        result = format_event_date(date_str)

        assert result == "25.12.2025 19:00"

    def test_format_event_date_empty(self):
        """Test formatting empty date."""
        result = format_event_date("")
        assert result == "TBD"

    def test_format_event_date_invalid(self):
        """Test formatting invalid date returns original."""
        result = format_event_date("invalid-date")
        assert result == "invalid-date"

    def test_build_events_list_message(self):
        """Test building event list message."""
        events = [
            {"fullActionName": "Concert Event", "actionDate": "2025-12-25T19:00:00", "minPrice": 1000},
            {"actionName": "Theater Show", "actionDate": "2025-12-26T20:00:00", "minPrice": 500},
        ]

        message = build_events_list_message(events, page=1, total_pages=1, lang="ru")

        assert "Страница 1 из 1" in message
        assert "Concert Event" in message
        assert "Theater Show" in message
        assert "1000" in message
        assert "500" in message

    def test_build_events_list_message_empty(self):
        """Test building message for empty events."""
        message = build_events_list_message([], page=1, total_pages=1, lang="ru")

        assert "нет" in message.lower() or "no_events" in message.lower()

    def test_build_pagination_keyboard_first_page(self):
        """Test keyboard on first page shows next button."""
        events = [{"actionId": 1, "fullActionName": "Event 1"}]

        keyboard = build_events_pagination_keyboard(events, page=1, total_pages=3, lang="ru")

        # Should have event buttons and pagination
        assert keyboard.inline_keyboard is not None

        # Find pagination row
        pagination_row = None
        for row in keyboard.inline_keyboard:
            for btn in row:
                if "events_page_" in (btn.callback_data or ""):
                    pagination_row = row
                    break

        assert pagination_row is not None
        # First page should have "next" but no "prev"
        callback_data = [btn.callback_data for btn in pagination_row]
        assert "events_page_2" in callback_data  # Next page
        assert "events_page_0" not in callback_data  # No prev on first page

    def test_build_pagination_keyboard_middle_page(self):
        """Test keyboard on middle page shows both prev and next."""
        events = [{"actionId": 1, "fullActionName": "Event 1"}]

        keyboard = build_events_pagination_keyboard(events, page=2, total_pages=3, lang="ru")

        # Find pagination row
        pagination_row = None
        for row in keyboard.inline_keyboard:
            for btn in row:
                if "events_page_" in (btn.callback_data or ""):
                    pagination_row = row
                    break

        assert pagination_row is not None
        callback_data = [btn.callback_data for btn in pagination_row]
        assert "events_page_1" in callback_data  # Prev page
        assert "events_page_3" in callback_data  # Next page

    def test_build_pagination_keyboard_last_page(self):
        """Test keyboard on last page shows prev but no next."""
        events = [{"actionId": 1, "fullActionName": "Event 1"}]

        keyboard = build_events_pagination_keyboard(events, page=3, total_pages=3, lang="ru")

        # Find pagination row
        pagination_row = None
        for row in keyboard.inline_keyboard:
            for btn in row:
                if "events_page_" in (btn.callback_data or ""):
                    pagination_row = row
                    break

        assert pagination_row is not None
        callback_data = [btn.callback_data for btn in pagination_row]
        assert "events_page_2" in callback_data  # Prev page
        assert "events_page_4" not in callback_data  # No next on last page

    def test_build_pagination_keyboard_single_page(self):
        """Test keyboard with single page shows no prev/next."""
        events = [{"actionId": 1, "fullActionName": "Event 1"}]

        keyboard = build_events_pagination_keyboard(events, page=1, total_pages=1, lang="ru")

        # Find pagination row
        has_pagination_buttons = False
        for row in keyboard.inline_keyboard:
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("events_page_"):
                    has_pagination_buttons = True

        # Single page should not have prev/next pagination buttons
        assert not has_pagination_buttons

    def test_build_pagination_keyboard_has_back_button(self):
        """Test keyboard always has back button."""
        events = [{"actionId": 1, "fullActionName": "Event 1"}]

        keyboard = build_events_pagination_keyboard(events, page=1, total_pages=1, lang="ru")

        # Find back button
        has_back_button = False
        for row in keyboard.inline_keyboard:
            for btn in row:
                if btn.callback_data == "back_to_main":
                    has_back_button = True

        assert has_back_button


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
