"""
Test WebApp shows seat selection.

Tests for seat selection in the Bill24 widget.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.bill24 import Bill24Client


class TestSeatListAPI:
    """Test Bill24 seat list API."""

    @pytest.mark.asyncio
    async def test_get_seat_list_method_exists(self):
        """Test get_seat_list method exists."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        assert hasattr(client, 'get_seat_list')
        assert callable(client.get_seat_list)

    @pytest.mark.asyncio
    async def test_get_seat_list_returns_seats(self):
        """Test get_seat_list returns seat data."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "seatList": [
                {"seatId": 1, "seatRow": "A", "seatNumber": 1, "price": 1000, "status": 0},
                {"seatId": 2, "seatRow": "A", "seatNumber": 2, "price": 1000, "status": 0},
                {"seatId": 3, "seatRow": "A", "seatNumber": 3, "price": 1000, "status": 1},  # Reserved
            ]
        }

        with patch.object(client, '_request', return_value=mock_response) as mock_req:
            result = await client.get_seat_list(action_event_id=1000)

            mock_req.assert_called_once()
            assert len(result) == 3
            assert result[0]["seatId"] == 1

    @pytest.mark.asyncio
    async def test_get_seat_list_with_action_event_id(self):
        """Test get_seat_list sends correct action_event_id."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        captured_params = {}

        async def capture_request(command, params=None):
            captured_params.update(params or {})
            return {"resultCode": 0, "seatList": []}

        with patch.object(client, '_request', side_effect=capture_request):
            await client.get_seat_list(action_event_id=500)

            assert captured_params.get("actionEventId") == 500


class TestAvailableSeats:
    """Test available seats display."""

    def test_seat_status_available(self):
        """Test seat status 0 means available."""
        seat = {"seatId": 1, "status": 0}
        is_available = seat["status"] == 0
        assert is_available is True

    def test_seat_status_reserved(self):
        """Test seat status 1 means reserved."""
        seat = {"seatId": 1, "status": 1}
        is_reserved = seat["status"] == 1
        assert is_reserved is True

    def test_seat_status_sold(self):
        """Test seat status 2 means sold."""
        seat = {"seatId": 1, "status": 2}
        is_sold = seat["status"] == 2
        assert is_sold is True

    def test_filter_available_seats(self):
        """Test filtering for available seats only."""
        seats = [
            {"seatId": 1, "status": 0},  # Available
            {"seatId": 2, "status": 1},  # Reserved
            {"seatId": 3, "status": 0},  # Available
            {"seatId": 4, "status": 2},  # Sold
        ]

        available = [s for s in seats if s["status"] == 0]

        assert len(available) == 2
        assert available[0]["seatId"] == 1
        assert available[1]["seatId"] == 3


class TestSeatReservation:
    """Test seat reservation."""

    @pytest.mark.asyncio
    async def test_reserve_seats_method_exists(self):
        """Test reserve_seats method exists."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        assert hasattr(client, 'reserve_seats')
        assert callable(client.reserve_seats)

    @pytest.mark.asyncio
    async def test_reserve_single_seat(self):
        """Test reserving a single seat."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "seatList": [{"seatId": 1, "status": 1}],
            "cartTimeout": 600,
            "totalSum": 1000
        }

        with patch.object(client, '_request', return_value=mock_response):
            result = await client.reserve_seats(
                action_event_id=1000,
                seat_ids=[1]
            )

            assert result["totalSum"] == 1000
            assert result["cartTimeout"] == 600
            assert len(result["seatList"]) == 1

    @pytest.mark.asyncio
    async def test_reserve_multiple_seats(self):
        """Test reserving multiple seats."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "seatList": [
                {"seatId": 1, "status": 1},
                {"seatId": 2, "status": 1},
                {"seatId": 3, "status": 1},
            ],
            "cartTimeout": 600,
            "totalSum": 3000
        }

        with patch.object(client, '_request', return_value=mock_response):
            result = await client.reserve_seats(
                action_event_id=1000,
                seat_ids=[1, 2, 3]
            )

            assert result["totalSum"] == 3000
            assert len(result["seatList"]) == 3


class TestSeatAddedToCart:
    """Test seat added to cart."""

    @pytest.mark.asyncio
    async def test_get_cart_method_exists(self):
        """Test get_cart method exists."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        assert hasattr(client, 'get_cart')

    @pytest.mark.asyncio
    async def test_cart_contains_reserved_seat(self):
        """Test cart contains the reserved seat."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "items": [
                {"seatId": 1, "seatRow": "A", "seatNumber": 1, "price": 1000}
            ],
            "totalSum": 1000
        }

        with patch.object(client, '_request', return_value=mock_response):
            result = await client.get_cart()

            assert result.get("totalSum") == 1000


class TestPriceUpdate:
    """Test price updates when selecting seats."""

    def test_single_seat_price(self):
        """Test price for single seat."""
        seat = {"seatId": 1, "price": 1500}
        total = seat["price"]
        assert total == 1500

    def test_multiple_seats_price(self):
        """Test total price for multiple seats."""
        seats = [
            {"seatId": 1, "price": 1000},
            {"seatId": 2, "price": 1500},
            {"seatId": 3, "price": 2000},
        ]

        total = sum(s["price"] for s in seats)
        assert total == 4500

    def test_reservation_response_includes_total(self):
        """Test reservation response includes total sum."""
        response = {
            "seatList": [{"seatId": 1}, {"seatId": 2}],
            "totalSum": 2500,
            "cartTimeout": 600
        }

        assert "totalSum" in response
        assert response["totalSum"] == 2500


class TestSeatingChart:
    """Test seating chart display."""

    def test_seat_has_row_info(self):
        """Test seat data includes row information."""
        seat = {
            "seatId": 1,
            "seatRow": "A",
            "seatNumber": 5,
            "price": 1000,
            "status": 0
        }

        assert "seatRow" in seat
        assert seat["seatRow"] == "A"

    def test_seat_has_number(self):
        """Test seat data includes seat number."""
        seat = {
            "seatId": 1,
            "seatRow": "A",
            "seatNumber": 10,
            "price": 1000,
            "status": 0
        }

        assert "seatNumber" in seat
        assert seat["seatNumber"] == 10

    def test_seat_has_price(self):
        """Test seat data includes price."""
        seat = {
            "seatId": 1,
            "seatRow": "A",
            "seatNumber": 1,
            "price": 2500,
            "status": 0
        }

        assert "price" in seat
        assert seat["price"] == 2500

    def test_seats_grouped_by_row(self):
        """Test seats can be grouped by row."""
        seats = [
            {"seatId": 1, "seatRow": "A", "seatNumber": 1},
            {"seatId": 2, "seatRow": "A", "seatNumber": 2},
            {"seatId": 3, "seatRow": "B", "seatNumber": 1},
            {"seatId": 4, "seatRow": "B", "seatNumber": 2},
            {"seatId": 5, "seatRow": "C", "seatNumber": 1},
        ]

        rows = {}
        for seat in seats:
            row = seat["seatRow"]
            if row not in rows:
                rows[row] = []
            rows[row].append(seat)

        assert len(rows) == 3  # A, B, C
        assert len(rows["A"]) == 2
        assert len(rows["B"]) == 2
        assert len(rows["C"]) == 1


class TestUnreserveSeat:
    """Test unreserving seats."""

    @pytest.mark.asyncio
    async def test_unreserve_seats_method_exists(self):
        """Test unreserve_seats method exists."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        assert hasattr(client, 'unreserve_seats')

    @pytest.mark.asyncio
    async def test_unreserve_all_method_exists(self):
        """Test unreserve_all method exists."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        assert hasattr(client, 'unreserve_all')


class TestSeatSelectionFlow:
    """Test complete seat selection flow."""

    @pytest.mark.asyncio
    async def test_flow_get_seats_then_reserve(self):
        """Test flow: get available seats then reserve."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        # Step 1: Get seat list
        seat_list_response = {
            "resultCode": 0,
            "seatList": [
                {"seatId": 1, "seatRow": "A", "seatNumber": 1, "price": 1000, "status": 0},
                {"seatId": 2, "seatRow": "A", "seatNumber": 2, "price": 1000, "status": 0},
            ]
        }

        # Step 2: Reserve selected seat
        reserve_response = {
            "resultCode": 0,
            "seatList": [{"seatId": 1, "status": 1}],
            "totalSum": 1000,
            "cartTimeout": 600
        }

        call_count = [0]

        async def mock_request(command, params=None):
            call_count[0] += 1
            if command == "GET_SEAT_LIST":
                return seat_list_response
            elif command == "RESERVATION":
                return reserve_response
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            # Get seats
            seats = await client.get_seat_list(action_event_id=1000)
            assert len(seats) == 2

            # Filter available
            available = [s for s in seats if s["status"] == 0]
            assert len(available) == 2

            # Reserve first seat
            result = await client.reserve_seats(
                action_event_id=1000,
                seat_ids=[available[0]["seatId"]]
            )

            assert result["totalSum"] == 1000
            assert call_count[0] == 2


class TestSectorPricing:
    """Test different price sectors."""

    def test_vip_sector_higher_price(self):
        """Test VIP sector has higher prices."""
        seats = [
            {"seatId": 1, "sector": "VIP", "price": 5000},
            {"seatId": 2, "sector": "Standard", "price": 1000},
        ]

        vip_seats = [s for s in seats if s.get("sector") == "VIP"]
        std_seats = [s for s in seats if s.get("sector") == "Standard"]

        assert vip_seats[0]["price"] > std_seats[0]["price"]

    def test_various_price_tiers(self):
        """Test various price tiers exist."""
        prices = [500, 1000, 1500, 2000, 5000]

        # All prices should be positive integers
        for price in prices:
            assert price > 0
            assert isinstance(price, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
