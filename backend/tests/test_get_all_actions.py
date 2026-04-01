"""
Integration test for GET_ALL_ACTIONS with real Bill24 API.

Uses credentials from .env.txt (FID=1311, TOKEN=5a99856515f919a4a2f9).
Tests both the API client and the event parsing logic in handlers.
"""
import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timezone


# Test credentials (Agent 68 in DB)
TEST_FID = 1311
TEST_TOKEN = "5a99856515f919a4a2f9"
TEST_ZONE = "test"


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestGetAllActions:
    """Integration tests for GET_ALL_ACTIONS API command."""

    @pytest.mark.asyncio
    async def test_get_all_actions_returns_events(self):
        """GET_ALL_ACTIONS should return a list of events for Agent 68."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=TEST_FID, token=TEST_TOKEN, zone=TEST_ZONE)
        try:
            response = await client.get_all_actions()

            # Verify response structure
            assert response.get("resultCode") == 0, f"Expected resultCode=0, got {response.get('resultCode')}"
            assert "actionList" in response, f"Response missing 'actionList'. Keys: {list(response.keys())}"

            events = response["actionList"]
            assert len(events) > 0, "No events returned for Agent 68 (fid=1311)"

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_event_has_required_fields(self):
        """Each event should have required fields per BIL24 protocol."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=TEST_FID, token=TEST_TOKEN, zone=TEST_ZONE)
        try:
            response = await client.get_all_actions()
            events = response.get("actionList", [])
            assert len(events) > 0, "No events to test"

            required_fields = [
                "actionId",
                "actionName",
                "fullActionName",
                "minPrice",
                "maxPrice",
                "firstEventDate",
                "lastEventDate",
                "age",
                "actionEventList",
            ]

            for event in events:
                for field in required_fields:
                    assert field in event, (
                        f"Event {event.get('actionId')} missing field '{field}'. "
                        f"Available keys: {list(event.keys())}"
                    )

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_event_date_format(self):
        """firstEventDate should be in dd.MM.yyyy format."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=TEST_FID, token=TEST_TOKEN, zone=TEST_ZONE)
        try:
            response = await client.get_all_actions()
            events = response.get("actionList", [])
            assert len(events) > 0

            for event in events:
                date_str = event.get("firstEventDate", "")
                assert len(date_str) == 10, f"Unexpected date length: '{date_str}'"
                assert date_str[2] == "." and date_str[5] == ".", (
                    f"Date not in dd.MM.yyyy format: '{date_str}'"
                )
                # Verify it parses correctly
                parsed = datetime.strptime(date_str, "%d.%m.%Y")
                assert parsed is not None

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_no_action_date_field(self):
        """Verify that 'actionDate' does NOT exist — use 'firstEventDate' instead."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=TEST_FID, token=TEST_TOKEN, zone=TEST_ZONE)
        try:
            response = await client.get_all_actions()
            events = response.get("actionList", [])
            assert len(events) > 0

            for event in events:
                assert "actionDate" not in event, (
                    f"Event {event.get('actionId')} unexpectedly has 'actionDate' field. "
                    f"The correct field is 'firstEventDate'."
                )

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_response_contains_reference_data(self):
        """GET_ALL_ACTIONS should also return countryList, cityList, etc."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=TEST_FID, token=TEST_TOKEN, zone=TEST_ZONE)
        try:
            response = await client.get_all_actions()

            for key in ["countryList", "cityList", "kindList", "genreList"]:
                assert key in response, f"Response missing '{key}'. Keys: {list(response.keys())}"

        finally:
            await client.close()


class TestFormatEventDate:
    """Test date formatting for Bill24 date formats."""

    def test_dd_mm_yyyy_format(self):
        """Should pass through dd.MM.yyyy format unchanged."""
        # Import from the handlers module
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "bot"))
        from app.bot.handlers import format_event_date

        assert format_event_date("01.11.2026") == "01.11.2026"
        assert format_event_date("30.09.2027") == "30.09.2027"

    def test_iso_format(self):
        """Should convert ISO format to dd.MM.yyyy HH:MM."""
        from app.bot.handlers import format_event_date

        result = format_event_date("2026-11-01T18:00:00Z")
        assert result == "01.11.2026 18:00"

    def test_empty_string(self):
        """Should return TBD for empty strings."""
        from app.bot.handlers import format_event_date

        assert format_event_date("") == "TBD"
        assert format_event_date(None) == "TBD"


class TestEventSorting:
    """Test event sorting by firstEventDate."""

    def test_sort_by_first_event_date(self):
        """Events should be sorted by firstEventDate in chronological order."""
        events = [
            {"fullActionName": "Event B", "firstEventDate": "30.09.2027"},
            {"fullActionName": "Event A", "firstEventDate": "01.11.2026"},
        ]

        def sort_key(event):
            date_str = event.get("firstEventDate", "")
            try:
                parts = date_str.split(".")
                if len(parts) == 3:
                    return f"{parts[2]}.{parts[1]}.{parts[0]}"
            except (ValueError, IndexError):
                pass
            return ""

        events.sort(key=sort_key)

        assert events[0]["fullActionName"] == "Event A"
        assert events[1]["fullActionName"] == "Event B"
