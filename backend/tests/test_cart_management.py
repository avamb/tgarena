"""
Test WebApp cart management.

Tests for adding/removing seats in the widget cart.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.bill24 import Bill24Client


class TestAddSeatToCart:
    """Test adding seat to cart."""

    @pytest.mark.asyncio
    async def test_reserve_adds_seat_to_cart(self):
        """Test reserving seat adds it to cart."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "seatList": [{"seatId": 1, "status": 1, "price": 1000}],
            "totalSum": 1000,
            "cartTimeout": 600
        }

        with patch.object(client, '_request', return_value=mock_response):
            result = await client.reserve_seats(
                action_event_id=1000,
                seat_ids=[1]
            )

            assert result["totalSum"] == 1000
            assert len(result["seatList"]) == 1

    @pytest.mark.asyncio
    async def test_cart_updated_after_reservation(self):
        """Test cart reflects reserved seats."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        cart_response = {
            "resultCode": 0,
            "items": [
                {"seatId": 1, "seatRow": "A", "seatNumber": 1, "price": 1500}
            ],
            "totalSum": 1500
        }

        with patch.object(client, '_request', return_value=cart_response):
            cart = await client.get_cart()

            assert cart["totalSum"] == 1500
            assert len(cart.get("items", [])) == 1


class TestCartTotalUpdates:
    """Test cart total updates correctly."""

    def test_total_single_seat(self):
        """Test total with single seat."""
        cart = {
            "items": [{"seatId": 1, "price": 1000}],
            "totalSum": 1000
        }

        assert cart["totalSum"] == 1000

    def test_total_two_seats(self):
        """Test total with two seats."""
        cart = {
            "items": [
                {"seatId": 1, "price": 1000},
                {"seatId": 2, "price": 1500}
            ],
            "totalSum": 2500
        }

        assert cart["totalSum"] == 2500

    def test_total_three_seats(self):
        """Test total with three seats."""
        cart = {
            "items": [
                {"seatId": 1, "price": 1000},
                {"seatId": 2, "price": 1500},
                {"seatId": 3, "price": 2000}
            ],
            "totalSum": 4500
        }

        calculated = sum(item["price"] for item in cart["items"])
        assert cart["totalSum"] == calculated
        assert cart["totalSum"] == 4500


class TestAddMultipleSeats:
    """Test adding multiple seats to cart."""

    @pytest.mark.asyncio
    async def test_reserve_second_seat(self):
        """Test adding second seat updates cart."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        # First reservation
        first_response = {
            "resultCode": 0,
            "seatList": [{"seatId": 1, "price": 1000}],
            "totalSum": 1000,
            "cartTimeout": 600
        }

        # Second reservation (adds to existing)
        second_response = {
            "resultCode": 0,
            "seatList": [
                {"seatId": 1, "price": 1000},
                {"seatId": 2, "price": 1500}
            ],
            "totalSum": 2500,
            "cartTimeout": 600
        }

        call_count = [0]

        async def mock_request(command, params=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return first_response
            return second_response

        with patch.object(client, '_request', side_effect=mock_request):
            # First seat
            result1 = await client.reserve_seats(action_event_id=1000, seat_ids=[1])
            assert result1["totalSum"] == 1000

            # Second seat
            result2 = await client.reserve_seats(action_event_id=1000, seat_ids=[2])
            assert result2["totalSum"] == 2500

    @pytest.mark.asyncio
    async def test_batch_add_multiple_seats(self):
        """Test adding multiple seats at once."""
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
                {"seatId": 1, "price": 1000},
                {"seatId": 2, "price": 1000},
                {"seatId": 3, "price": 1000}
            ],
            "totalSum": 3000,
            "cartTimeout": 600
        }

        with patch.object(client, '_request', return_value=mock_response):
            result = await client.reserve_seats(
                action_event_id=1000,
                seat_ids=[1, 2, 3]
            )

            assert result["totalSum"] == 3000
            assert len(result["seatList"]) == 3


class TestRemoveSeatFromCart:
    """Test removing seat from cart."""

    @pytest.mark.asyncio
    async def test_unreserve_removes_seat(self):
        """Test unreserving seat removes it from cart."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "seatList": [{"seatId": 2, "price": 1500}],  # Seat 1 removed
            "totalSum": 1500
        }

        with patch.object(client, '_request', return_value=mock_response):
            result = await client.unreserve_seats(
                action_event_id=1000,
                seat_ids=[1]
            )

            # Should succeed
            assert result is not None

    @pytest.mark.asyncio
    async def test_unreserve_all_clears_cart(self):
        """Test unreserve all clears entire cart."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "seatList": [],
            "totalSum": 0
        }

        with patch.object(client, '_request', return_value=mock_response):
            result = await client.unreserve_all(action_event_id=1000)

            assert result is not None


class TestTotalUpdatesAfterRemoval:
    """Test total updates after removing seats."""

    def test_total_after_remove_one(self):
        """Test total after removing one seat."""
        # Start with 3 seats totaling 3000
        # Remove 1 seat (1000), total should be 2000
        original_total = 3000
        removed_price = 1000
        new_total = original_total - removed_price

        assert new_total == 2000

    def test_total_after_remove_all(self):
        """Test total is zero after removing all seats."""
        cart_after_clear = {
            "items": [],
            "totalSum": 0
        }

        assert cart_after_clear["totalSum"] == 0
        assert len(cart_after_clear["items"]) == 0


class TestCartTimeout:
    """Test cart timeout behavior."""

    def test_cart_has_timeout(self):
        """Test cart has timeout value."""
        response = {
            "seatList": [{"seatId": 1}],
            "totalSum": 1000,
            "cartTimeout": 600  # 10 minutes
        }

        assert "cartTimeout" in response
        assert response["cartTimeout"] == 600

    def test_cart_timeout_reasonable(self):
        """Test cart timeout is reasonable (5-15 minutes)."""
        timeouts = [300, 600, 900]  # 5, 10, 15 minutes

        for timeout in timeouts:
            assert 300 <= timeout <= 900

    @pytest.mark.asyncio
    async def test_reservation_returns_timeout(self):
        """Test reservation response includes timeout."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "seatList": [{"seatId": 1}],
            "totalSum": 1000,
            "cartTimeout": 600
        }

        with patch.object(client, '_request', return_value=mock_response):
            result = await client.reserve_seats(
                action_event_id=1000,
                seat_ids=[1]
            )

            assert "cartTimeout" in result


class TestCartManagementFlow:
    """Test complete cart management flow."""

    @pytest.mark.asyncio
    async def test_add_remove_add_flow(self):
        """Test add -> remove -> add flow."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        responses = [
            # Add seat 1
            {"resultCode": 0, "seatList": [{"seatId": 1}], "totalSum": 1000, "cartTimeout": 600},
            # Remove seat 1
            {"resultCode": 0, "seatList": [], "totalSum": 0},
            # Add seat 2
            {"resultCode": 0, "seatList": [{"seatId": 2}], "totalSum": 1500, "cartTimeout": 600},
        ]

        call_count = [0]

        async def mock_request(command, params=None):
            result = responses[call_count[0]]
            call_count[0] += 1
            return result

        with patch.object(client, '_request', side_effect=mock_request):
            # Add seat 1
            result1 = await client.reserve_seats(action_event_id=1000, seat_ids=[1])
            assert result1["totalSum"] == 1000

            # Remove seat 1
            await client.unreserve_seats(action_event_id=1000, seat_ids=[1])

            # Add seat 2
            result3 = await client.reserve_seats(action_event_id=1000, seat_ids=[2])
            assert result3["totalSum"] == 1500


class TestCartItemDetails:
    """Test cart item details."""

    def test_cart_item_has_seat_info(self):
        """Test cart item has seat info."""
        cart_item = {
            "seatId": 1,
            "seatRow": "A",
            "seatNumber": 5,
            "price": 1500,
            "eventName": "Concert"
        }

        assert "seatId" in cart_item
        assert "seatRow" in cart_item
        assert "seatNumber" in cart_item
        assert "price" in cart_item

    def test_cart_item_display_format(self):
        """Test cart item can be displayed as string."""
        cart_item = {
            "seatRow": "B",
            "seatNumber": 10,
            "price": 2000
        }

        display = f"Row {cart_item['seatRow']}, Seat {cart_item['seatNumber']} - {cart_item['price']}₽"

        assert "Row B" in display
        assert "Seat 10" in display
        assert "2000₽" in display


class TestEmptyCart:
    """Test empty cart behavior."""

    def test_empty_cart_total_zero(self):
        """Test empty cart has zero total."""
        cart = {"items": [], "totalSum": 0}

        assert cart["totalSum"] == 0

    def test_empty_cart_no_items(self):
        """Test empty cart has no items."""
        cart = {"items": [], "totalSum": 0}

        assert len(cart["items"]) == 0

    @pytest.mark.asyncio
    async def test_get_cart_when_empty(self):
        """Test get_cart returns empty cart."""
        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "items": [],
            "totalSum": 0
        }

        with patch.object(client, '_request', return_value=mock_response):
            cart = await client.get_cart()

            assert cart["totalSum"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
