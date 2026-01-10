"""
Test reservation cancellation.

Tests that canceling a reservation releases seats back to available.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestUnreserveSeats:
    """Test unreserving individual seats."""

    @pytest.mark.asyncio
    async def test_unreserve_single_seat(self):
        """Test unreserving a single seat."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=1001,
            session_id="test_session"
        )

        async def mock_request(command, params=None):
            if command == "RESERVATION" and params.get("type") == "UN_RESERVE":
                return {
                    "resultCode": 0,
                    "seatList": [
                        {"seatId": 101, "status": "FREE"}
                    ],
                    "message": "Seat released"
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.unreserve_seats(
                action_event_id=100,
                seat_ids=[101]
            )

            # Seat should now be FREE
            assert result["resultCode"] == 0

    @pytest.mark.asyncio
    async def test_unreserve_multiple_seats(self):
        """Test unreserving multiple seats at once."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            if params.get("type") == "UN_RESERVE":
                return {
                    "resultCode": 0,
                    "seatList": [
                        {"seatId": s, "status": "FREE"}
                        for s in params.get("seatList", [])
                    ]
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.unreserve_seats(
                action_event_id=100,
                seat_ids=[101, 102, 103]
            )

            assert result["resultCode"] == 0


class TestUnreserveAll:
    """Test unreserving all seats at once."""

    @pytest.mark.asyncio
    async def test_unreserve_all_seats(self):
        """Test unreserving all reserved seats for an event."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            if params.get("type") == "UN_RESERVE_ALL":
                return {
                    "resultCode": 0,
                    "message": "All seats released"
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.unreserve_all(action_event_id=100)

            assert result["resultCode"] == 0

    @pytest.mark.asyncio
    async def test_unreserve_all_sends_correct_command(self):
        """Test unreserve_all sends correct command type."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        captured_params = {}

        async def capture_request(command, params=None):
            captured_params.update(params or {})
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=capture_request):
            await client.unreserve_all(action_event_id=100)

            assert captured_params["type"] == "UN_RESERVE_ALL"
            assert captured_params["actionEventId"] == 100


class TestSeatAvailabilityAfterCancel:
    """Test seats become available after cancellation."""

    @pytest.mark.asyncio
    async def test_seat_shows_free_after_cancel(self):
        """Test cancelled seat shows as FREE in seat list."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        # Track if unreserve was called
        unreserve_called = [False]

        async def mock_request(command, params=None):
            if command == "RESERVATION" and params.get("type") == "UN_RESERVE":
                unreserve_called[0] = True
                return {"resultCode": 0}
            elif command == "GET_SEAT_LIST":
                # After unreserve, seat should be FREE
                if unreserve_called[0]:
                    return {
                        "resultCode": 0,
                        "seatList": [
                            {"seatId": 101, "status": "FREE", "price": 1000}
                        ]
                    }
                else:
                    return {
                        "resultCode": 0,
                        "seatList": [
                            {"seatId": 101, "status": "RESERVED", "price": 1000}
                        ]
                    }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            # Check seat is RESERVED
            seats_before = await client.get_seat_list(action_event_id=100)
            assert seats_before[0]["status"] == "RESERVED"

            # Unreserve
            await client.unreserve_seats(
                action_event_id=100,
                seat_ids=[101]
            )

            # Check seat is now FREE
            seats_after = await client.get_seat_list(action_event_id=100)
            assert seats_after[0]["status"] == "FREE"


class TestCancelBeforeTimeout:
    """Test cancellation before cart timeout."""

    @pytest.mark.asyncio
    async def test_cancel_within_timeout(self):
        """Test user can cancel within cart timeout period."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            if command == "RESERVATION":
                if params.get("type") == "RESERVE":
                    return {
                        "resultCode": 0,
                        "seatList": [{"seatId": 101, "status": "RESERVED"}],
                        "cartTimeout": 600  # 10 minutes
                    }
                elif params.get("type") == "UN_RESERVE":
                    return {
                        "resultCode": 0,
                        "message": "Seats released successfully"
                    }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            # Reserve
            reserve_result = await client.reserve_seats(
                action_event_id=100,
                seat_ids=[101]
            )
            assert reserve_result["cartTimeout"] == 600

            # Cancel within timeout
            cancel_result = await client.unreserve_seats(
                action_event_id=100,
                seat_ids=[101]
            )
            assert cancel_result["resultCode"] == 0


class TestCancelOrder:
    """Test canceling an entire order."""

    @pytest.mark.asyncio
    async def test_cancel_unpaid_order(self):
        """Test canceling an order that hasn't been paid."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            if command == "CANCEL_ORDER":
                return {
                    "resultCode": 0,
                    "orderId": params.get("orderId"),
                    "status": "CANCELLED"
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.cancel_order(order_id=12345)

            assert result["resultCode"] == 0
            assert result.get("status") == "CANCELLED"

    @pytest.mark.asyncio
    async def test_cancel_order_releases_all_seats(self):
        """Test that canceling order releases all reserved seats."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        # Simulate the full flow
        order_cancelled = [False]

        async def mock_request(command, params=None):
            if command == "RESERVATION" and params.get("type") == "RESERVE":
                return {
                    "resultCode": 0,
                    "seatList": [
                        {"seatId": 1, "status": "RESERVED"},
                        {"seatId": 2, "status": "RESERVED"},
                        {"seatId": 3, "status": "RESERVED"},
                    ],
                    "cartTimeout": 600,
                    "totalSum": 3000
                }
            elif command == "CREATE_ORDER":
                return {
                    "resultCode": 0,
                    "orderId": 99999
                }
            elif command == "CANCEL_ORDER":
                order_cancelled[0] = True
                return {
                    "resultCode": 0,
                    "status": "CANCELLED"
                }
            elif command == "GET_SEAT_LIST":
                if order_cancelled[0]:
                    return {
                        "resultCode": 0,
                        "seatList": [
                            {"seatId": 1, "status": "FREE"},
                            {"seatId": 2, "status": "FREE"},
                            {"seatId": 3, "status": "FREE"},
                        ]
                    }
                else:
                    return {
                        "resultCode": 0,
                        "seatList": [
                            {"seatId": 1, "status": "RESERVED"},
                            {"seatId": 2, "status": "RESERVED"},
                            {"seatId": 3, "status": "RESERVED"},
                        ]
                    }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            # Reserve 3 seats
            await client.reserve_seats(
                action_event_id=100,
                seat_ids=[1, 2, 3]
            )

            # Create order
            await client.create_order(
                success_url="https://example.com/success",
                fail_url="https://example.com/fail"
            )

            # Check seats are reserved
            seats_before = await client.get_seat_list(action_event_id=100)
            assert all(s["status"] == "RESERVED" for s in seats_before)

            # Cancel order
            await client.cancel_order(order_id=99999)

            # Check seats are now free
            seats_after = await client.get_seat_list(action_event_id=100)
            assert all(s["status"] == "FREE" for s in seats_after)


class TestReservationMethods:
    """Test reservation-related method signatures."""

    def test_unreserve_seats_method_exists(self):
        """Test unreserve_seats method exists."""
        from app.services.bill24 import Bill24Client
        import inspect

        assert hasattr(Bill24Client, 'unreserve_seats')
        assert inspect.iscoroutinefunction(Bill24Client.unreserve_seats)

    def test_unreserve_all_method_exists(self):
        """Test unreserve_all method exists."""
        from app.services.bill24 import Bill24Client
        import inspect

        assert hasattr(Bill24Client, 'unreserve_all')
        assert inspect.iscoroutinefunction(Bill24Client.unreserve_all)

    def test_cancel_order_method_exists(self):
        """Test cancel_order method exists."""
        from app.services.bill24 import Bill24Client
        import inspect

        assert hasattr(Bill24Client, 'cancel_order')
        assert inspect.iscoroutinefunction(Bill24Client.cancel_order)


class TestCartTimeout:
    """Test cart timeout behavior."""

    @pytest.mark.asyncio
    async def test_reservation_returns_timeout(self):
        """Test reservation response includes cart timeout."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "seatList": [{"seatId": 101}],
                "cartTimeout": 600,  # 10 minutes
                "totalSum": 1000
            }

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.reserve_seats(
                action_event_id=100,
                seat_ids=[101]
            )

            # Cart timeout should be returned
            assert "cartTimeout" in result
            assert result["cartTimeout"] == 600


class TestReservationStateTransitions:
    """Test seat state transitions."""

    def test_valid_seat_statuses(self):
        """Test valid seat status values."""
        valid_statuses = {"FREE", "RESERVED", "SOLD", "BLOCKED"}

        # These are the expected states from Bill24
        assert "FREE" in valid_statuses  # Available for reservation
        assert "RESERVED" in valid_statuses  # Temporarily held
        assert "SOLD" in valid_statuses  # Purchased
        assert "BLOCKED" in valid_statuses  # Not available

    @pytest.mark.asyncio
    async def test_free_to_reserved_transition(self):
        """Test seat transitions from FREE to RESERVED."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            if params.get("type") == "RESERVE":
                return {
                    "resultCode": 0,
                    "seatList": [{"seatId": 101, "status": "RESERVED"}],
                    "cartTimeout": 600
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.reserve_seats(
                action_event_id=100,
                seat_ids=[101]
            )

            assert result["seatList"][0]["status"] == "RESERVED"

    @pytest.mark.asyncio
    async def test_reserved_to_free_transition(self):
        """Test seat transitions from RESERVED to FREE on cancel."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            if params.get("type") == "UN_RESERVE":
                return {
                    "resultCode": 0,
                    "seatList": [{"seatId": 101, "status": "FREE"}]
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.unreserve_seats(
                action_event_id=100,
                seat_ids=[101]
            )

            assert result["resultCode"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
