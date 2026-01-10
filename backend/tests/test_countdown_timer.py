"""
Test event countdown timer.

Tests countdown calculation and display for events.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.handlers import calculate_countdown, build_event_details_message
from app.bot.localization import get_text


class TestCountdownCalculation:
    """Test calculate_countdown function."""

    def test_countdown_days_and_hours(self):
        """Test countdown shows days and hours."""
        # Event 3 days and 5 hours from now
        future_date = datetime.now(timezone.utc) + timedelta(days=3, hours=5)
        date_str = future_date.isoformat()

        result = calculate_countdown(date_str, "ru")

        assert "дн." in result  # Russian days
        assert "ч." in result   # Russian hours

    def test_countdown_hours_and_minutes(self):
        """Test countdown shows hours and minutes when less than a day."""
        # Event 5 hours and 30 minutes from now
        future_date = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        date_str = future_date.isoformat()

        result = calculate_countdown(date_str, "ru")

        assert "ч." in result    # Russian hours
        assert "мин." in result  # Russian minutes
        assert "дн." not in result  # No days

    def test_countdown_minutes_only(self):
        """Test countdown shows minutes only when less than an hour."""
        # Event 45 minutes from now
        future_date = datetime.now(timezone.utc) + timedelta(minutes=45)
        date_str = future_date.isoformat()

        result = calculate_countdown(date_str, "ru")

        assert "мин." in result  # Russian minutes

    def test_countdown_started_event(self):
        """Test countdown shows 'started' for past events."""
        # Event started 1 hour ago
        past_date = datetime.now(timezone.utc) - timedelta(hours=1)
        date_str = past_date.isoformat()

        result = calculate_countdown(date_str, "ru")

        assert "началось" in result.lower()

    def test_countdown_english(self):
        """Test countdown in English."""
        # Event 2 days from now
        future_date = datetime.now(timezone.utc) + timedelta(days=2, hours=3)
        date_str = future_date.isoformat()

        result = calculate_countdown(date_str, "en")

        assert "d" in result  # English days
        assert "h" in result  # English hours

    def test_countdown_empty_date(self):
        """Test countdown with empty date returns empty string."""
        result = calculate_countdown("", "ru")
        assert result == ""

    def test_countdown_none_date(self):
        """Test countdown with None date returns empty string."""
        result = calculate_countdown(None, "ru")
        assert result == ""

    def test_countdown_invalid_date(self):
        """Test countdown with invalid date returns empty string."""
        result = calculate_countdown("not-a-date", "ru")
        assert result == ""

    def test_countdown_z_suffix(self):
        """Test countdown handles Z suffix in ISO date."""
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        date_str = future_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        result = calculate_countdown(date_str, "ru")

        assert result != ""  # Should produce a valid countdown

    def test_countdown_starting_soon(self):
        """Test countdown shows 'starting soon' when very close."""
        # Event just seconds from now
        future_date = datetime.now(timezone.utc) + timedelta(seconds=30)
        date_str = future_date.isoformat()

        result = calculate_countdown(date_str, "ru")

        assert result != ""  # Should produce something


class TestCountdownInEventDetails:
    """Test countdown integration in event details."""

    def test_event_details_includes_countdown(self):
        """Test event details message includes countdown."""
        future_date = datetime.now(timezone.utc) + timedelta(days=2, hours=5)

        event = {
            "fullActionName": "Test Concert",
            "actionDate": future_date.isoformat(),
            "venueName": "Test Venue",
            "minPrice": 1000,
            "maxPrice": 3000,
            "ageRestriction": 0
        }

        result = build_event_details_message(event, "ru")

        assert "Test Concert" in result
        assert "До начала" in result  # Russian countdown label
        assert "дн." in result  # Should show days

    def test_event_details_no_countdown_for_past_event(self):
        """Test event details shows 'started' for past events."""
        past_date = datetime.now(timezone.utc) - timedelta(hours=1)

        event = {
            "fullActionName": "Past Concert",
            "actionDate": past_date.isoformat(),
            "venueName": "Test Venue",
            "minPrice": 500,
            "maxPrice": 1500,
            "ageRestriction": 0
        }

        result = build_event_details_message(event, "ru")

        assert "Past Concert" in result
        assert "началось" in result.lower()

    def test_event_details_english_countdown(self):
        """Test event details with English countdown."""
        future_date = datetime.now(timezone.utc) + timedelta(days=5)

        event = {
            "fullActionName": "English Concert",
            "actionDate": future_date.isoformat(),
            "venueName": "Test Venue",
            "minPrice": 2000,
            "maxPrice": 5000,
            "ageRestriction": 18
        }

        result = build_event_details_message(event, "en")

        assert "English Concert" in result
        assert "Starts in" in result  # English countdown label


class TestCountdownLocalization:
    """Test countdown localization strings."""

    def test_russian_countdown_days(self):
        """Test Russian countdown days format."""
        text = get_text("countdown_days", "ru", count=5)
        assert "5" in text
        assert "дн." in text

    def test_russian_countdown_hours(self):
        """Test Russian countdown hours format."""
        text = get_text("countdown_hours", "ru", count=3)
        assert "3" in text
        assert "ч." in text

    def test_russian_countdown_minutes(self):
        """Test Russian countdown minutes format."""
        text = get_text("countdown_minutes", "ru", count=45)
        assert "45" in text
        assert "мин." in text

    def test_english_countdown_days(self):
        """Test English countdown days format."""
        text = get_text("countdown_days", "en", count=7)
        assert "7" in text
        assert "d" in text

    def test_english_countdown_hours(self):
        """Test English countdown hours format."""
        text = get_text("countdown_hours", "en", count=12)
        assert "12" in text
        assert "h" in text

    def test_english_countdown_minutes(self):
        """Test English countdown minutes format."""
        text = get_text("countdown_minutes", "en", count=30)
        assert "30" in text
        assert "m" in text

    def test_countdown_label_has_placeholder(self):
        """Test countdown label contains countdown placeholder."""
        ru_text = get_text("countdown_label", "ru", countdown="2 дн. 5 ч.")
        en_text = get_text("countdown_label", "en", countdown="2d 5h")

        assert "2 дн. 5 ч." in ru_text
        assert "2d 5h" in en_text


class TestCountdownEdgeCases:
    """Test edge cases for countdown."""

    def test_countdown_exactly_one_day(self):
        """Test countdown for exactly one day."""
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        date_str = future_date.isoformat()

        result = calculate_countdown(date_str, "ru")

        assert "1" in result
        assert "дн." in result

    def test_countdown_large_number_of_days(self):
        """Test countdown for many days."""
        future_date = datetime.now(timezone.utc) + timedelta(days=365)
        date_str = future_date.isoformat()

        result = calculate_countdown(date_str, "ru")

        assert "365" in result or "дн." in result

    def test_countdown_timezone_handling(self):
        """Test countdown handles timezone-naive dates."""
        # Create a naive datetime (no timezone)
        future_date = datetime.utcnow() + timedelta(days=1)
        date_str = future_date.isoformat()  # No timezone info

        result = calculate_countdown(date_str, "ru")

        # Should still work and produce a countdown
        assert result != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
