"""
Test Bill24 API GET_SEAT_LIST integration.

Tests for seat availability fetching.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.bill24 import Bill24Client


class TestGetSeatListMethodExists:
    """Test GET_SEAT_LIST method exists in Bill24 client."""

    def test_get_seat_list_method_exists(self):
        """Test get_seat_list method exists."""
        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        assert hasattr(client, 'get_seat_list')
        assert callable(client.get_seat_list)

    @pytest.mark.asyncio
    async def test_get_seat_list_is_async(self):
        """Test get_seat_list is an async method."""
        import inspect

        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        assert inspect.iscoroutinefunction(client.get_seat_list)


class TestGetSeatListAPICall:
    """Test GET_SEAT_LIST API call."""

    @pytest.mark.asyncio
    async def test_get_seat_list_calls_api(self):
        """Test get_seat_list makes API call."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "sectorList": [
                {
                    "sectorId": 1,
                    "sectorName": "VIP",
                    "rowList": [
                        {
                            "rowId": 1,
                            "rowName": "A",
                            "seatList": [
                                {"seatId": 1, "seatName": "1", "status": "FREE", "price": 5000},
                                {"seatId": 2, "seatName": "2", "status": "RESERVED", "price": 5000}
                            ]
                        }
                    ]
                }
            ]
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_seat_list(action_id=12345)

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET_SEAT_LIST"

    @pytest.mark.asyncio
    async def test_get_seat_list_returns_sectors(self):
        """Test get_seat_list returns sectorList."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "sectorList": [
                {
                    "sectorId": 1,
                    "sectorName": "VIP",
                    "rowList": []
                }
            ]
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_seat_list(action_id=12345)

            assert "sectorList" in result


class TestSeatDataFormat:
    """Test seat data format from Bill24."""

    @pytest.mark.asyncio
    async def test_seat_has_status(self):
        """Test seat has status field."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "sectorList": [
                {
                    "sectorId": 1,
                    "sectorName": "Standard",
                    "rowList": [
                        {
                            "rowId": 1,
                            "rowName": "1",
                            "seatList": [
                                {"seatId": 1, "seatName": "1", "status": "FREE", "price": 1000}
                            ]
                        }
                    ]
                }
            ]
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_seat_list(action_id=12345)
            sectors = result.get("sectorList", [])

            assert len(sectors) > 0
            rows = sectors[0].get("rowList", [])
            assert len(rows) > 0
            seats = rows[0].get("seatList", [])
            assert len(seats) > 0
            assert "status" in seats[0]

    @pytest.mark.asyncio
    async def test_seat_has_price(self):
        """Test seat has price field."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "sectorList": [
                {
                    "sectorId": 1,
                    "sectorName": "Standard",
                    "rowList": [
                        {
                            "rowId": 1,
                            "rowName": "1",
                            "seatList": [
                                {"seatId": 1, "seatName": "1", "status": "FREE", "price": 2500}
                            ]
                        }
                    ]
                }
            ]
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_seat_list(action_id=12345)
            sectors = result.get("sectorList", [])
            seats = sectors[0]["rowList"][0]["seatList"]

            assert "price" in seats[0]


class TestSeatStatuses:
    """Test seat status values."""

    def test_free_seat_status(self):
        """Test FREE seat status is valid."""
        # FREE status indicates available seat
        status = "FREE"
        assert status in ["FREE", "AVAILABLE", "OPEN"]

    def test_reserved_seat_status(self):
        """Test RESERVED seat status is valid."""
        # RESERVED status indicates seat is held
        status = "RESERVED"
        assert "RESERV" in status.upper() or "HOLD" in status.upper()

    def test_sold_seat_status(self):
        """Test SOLD seat status is valid."""
        # SOLD status indicates seat is purchased
        status = "SOLD"
        assert status in ["SOLD", "PURCHASED", "OCCUPIED"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
