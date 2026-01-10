"""
Test Bill24 API GET_ALL_ACTIONS integration.

Tests for event fetching from Bill24 API.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.bill24 import Bill24Client


class TestGetAllActionsMethodExists:
    """Test GET_ALL_ACTIONS method exists in Bill24 client."""

    def test_get_all_actions_method_exists(self):
        """Test get_all_actions method exists."""
        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test"
        )

        assert hasattr(client, 'get_all_actions')
        assert callable(client.get_all_actions)

    @pytest.mark.asyncio
    async def test_get_all_actions_is_async(self):
        """Test get_all_actions is an async method."""
        import inspect

        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test"
        )

        assert inspect.iscoroutinefunction(client.get_all_actions)


class TestGetAllActionsAPICall:
    """Test GET_ALL_ACTIONS API call."""

    @pytest.mark.asyncio
    async def test_get_all_actions_calls_api(self):
        """Test get_all_actions makes API call."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        mock_response = {
            "resultCode": 0,
            "actionList": [
                {
                    "actionId": 1,
                    "actionName": "Test Event",
                    "fullActionName": "Test Event Full Name",
                    "actionDate": "2026-01-15T19:00:00",
                    "minPrice": 1000,
                    "maxPrice": 5000
                }
            ]
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_all_actions()

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET_ALL_ACTIONS"

    @pytest.mark.asyncio
    async def test_get_all_actions_returns_action_list(self):
        """Test get_all_actions returns actionList."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        mock_response = {
            "resultCode": 0,
            "actionList": [
                {
                    "actionId": 1,
                    "actionName": "Test Event",
                    "fullActionName": "Test Event Full Name",
                    "actionDate": "2026-01-15T19:00:00",
                    "minPrice": 1000,
                    "maxPrice": 5000
                }
            ]
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_all_actions()

            assert "actionList" in result


class TestEventDataFormat:
    """Test event data format from Bill24."""

    @pytest.mark.asyncio
    async def test_event_has_action_id(self):
        """Test event has actionId."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        mock_response = {
            "resultCode": 0,
            "actionList": [
                {
                    "actionId": 12345,
                    "actionName": "Test Event",
                    "actionDate": "2026-01-15T19:00:00"
                }
            ]
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_all_actions()
            events = result.get("actionList", [])

            assert len(events) > 0
            assert "actionId" in events[0]

    @pytest.mark.asyncio
    async def test_event_has_name(self):
        """Test event has actionName or fullActionName."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        mock_response = {
            "resultCode": 0,
            "actionList": [
                {
                    "actionId": 12345,
                    "actionName": "Test Event",
                    "fullActionName": "Full Test Event Name",
                    "actionDate": "2026-01-15T19:00:00"
                }
            ]
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_all_actions()
            events = result.get("actionList", [])

            assert len(events) > 0
            assert "actionName" in events[0] or "fullActionName" in events[0]

    @pytest.mark.asyncio
    async def test_event_has_date(self):
        """Test event has actionDate."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        mock_response = {
            "resultCode": 0,
            "actionList": [
                {
                    "actionId": 12345,
                    "actionName": "Test Event",
                    "actionDate": "2026-01-15T19:00:00"
                }
            ]
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_all_actions()
            events = result.get("actionList", [])

            assert len(events) > 0
            assert "actionDate" in events[0]


class TestFetchEventsFromBill24:
    """Test fetch_events_from_bill24 helper function."""

    def test_fetch_events_function_exists(self):
        """Test fetch_events_from_bill24 function exists."""
        from app.bot.handlers import fetch_events_from_bill24

        assert callable(fetch_events_from_bill24)

    @pytest.mark.asyncio
    async def test_fetch_events_is_async(self):
        """Test fetch_events_from_bill24 is async."""
        import inspect
        from app.bot.handlers import fetch_events_from_bill24

        assert inspect.iscoroutinefunction(fetch_events_from_bill24)


class TestEventCaching:
    """Test event caching with Redis."""

    def test_bill24_client_uses_agent_fid(self):
        """Test Bill24Client uses agent FID."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test"
        )

        assert client.fid == 1271


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
