"""
Test filter events by date.

Tests for event date filtering in the bot.
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestEventSorting:
    """Test events are sorted by date."""

    def test_events_sorted_by_date(self):
        """Test fetch_events_from_bill24 sorts events by date."""
        import inspect
        from app.bot.handlers import fetch_events_from_bill24

        source = inspect.getsource(fetch_events_from_bill24)

        # Should sort events by actionDate
        assert "sort" in source.lower()
        assert "actionDate" in source


class TestDateFormatting:
    """Test event date formatting."""

    def test_format_event_date_function_exists(self):
        """Test format_event_date function exists."""
        from app.bot.handlers import format_event_date

        assert callable(format_event_date)

    def test_format_event_date_formats_correctly(self):
        """Test date formatting produces readable format."""
        from app.bot.handlers import format_event_date

        # Test various date formats
        date_str = "2026-01-15T19:00:00"
        result = format_event_date(date_str)

        # Should produce human-readable format (DD.MM.YYYY HH:MM)
        assert len(result) > 0
        assert "15" in result  # Day
        assert "01" in result or "Jan" in result  # Month
        assert "2026" in result  # Year

    def test_format_event_date_handles_empty(self):
        """Test format_event_date handles empty string."""
        from app.bot.handlers import format_event_date

        result = format_event_date("")
        assert result == "TBD"

    def test_format_event_date_handles_none(self):
        """Test format_event_date handles None."""
        from app.bot.handlers import format_event_date

        result = format_event_date(None)
        # Should not crash
        assert result is not None


class TestEventCountdown:
    """Test event countdown functionality."""

    def test_calculate_countdown_function_exists(self):
        """Test calculate_countdown function exists."""
        from app.bot.handlers import calculate_countdown

        assert callable(calculate_countdown)

    def test_countdown_for_future_event(self):
        """Test countdown shows time remaining for future events."""
        from app.bot.handlers import calculate_countdown

        # Create a date 2 days in the future
        future_date = (datetime.now() + timedelta(days=2, hours=5)).isoformat()
        result = calculate_countdown(future_date, "ru")

        # Should show days and hours
        assert len(result) > 0
        # Should contain countdown parts (days, hours)
        assert "дн" in result.lower() or "ч" in result.lower() or "d" in result.lower()

    def test_countdown_for_past_event(self):
        """Test countdown shows 'started' for past events."""
        from app.bot.handlers import calculate_countdown
        from app.bot.localization import get_text

        # Create a date in the past
        past_date = (datetime.now() - timedelta(days=1)).isoformat()
        result = calculate_countdown(past_date, "ru")

        # Should show "already started" message
        expected = get_text("countdown_started", "ru")
        assert result == expected

    def test_countdown_handles_empty_date(self):
        """Test countdown handles empty date."""
        from app.bot.handlers import calculate_countdown

        result = calculate_countdown("", "ru")
        assert result == ""


class TestEventListDisplayByDate:
    """Test event list displays events by date."""

    def test_event_list_item_includes_date(self):
        """Test event list item format includes date."""
        from app.bot.localization import get_text

        text = get_text("event_list_item", "ru",
                       number=1,
                       name="Test Event",
                       date="15.01.2026",
                       min_price=1000)

        # Should include date
        assert "15.01.2026" in text

    def test_event_details_includes_date(self):
        """Test event details format includes date."""
        from app.bot.localization import get_text

        text = get_text("event_details", "ru",
                       name="Concert",
                       date="15.01.2026 19:00",
                       venue="Arena",
                       min_price=1000,
                       max_price=5000,
                       age_restriction="",
                       countdown="")

        # Should include date
        assert "15.01.2026" in text or "19:00" in text


class TestPagination:
    """Test event pagination respects date order."""

    def test_get_page_events_function_exists(self):
        """Test get_page_events function exists."""
        from app.bot.handlers import get_page_events

        assert callable(get_page_events)

    def test_get_page_events_returns_tuple(self):
        """Test get_page_events returns (events, total_pages)."""
        from app.bot.handlers import get_page_events

        events = [
            {"actionId": 1, "actionDate": "2026-01-15"},
            {"actionId": 2, "actionDate": "2026-01-20"},
            {"actionId": 3, "actionDate": "2026-01-25"},
        ]

        page_events, total_pages = get_page_events(events, page=1)

        assert isinstance(page_events, list)
        assert isinstance(total_pages, int)
        assert total_pages >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
