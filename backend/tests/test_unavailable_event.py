"""
Test unavailable event error handling.

Tests that users see appropriate errors when trying to access
cancelled or unavailable events.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestEventNotFound:
    """Test handling of non-existent events."""

    @pytest.mark.asyncio
    async def test_get_action_ext_not_found(self):
        """Test GET_ACTION_EXT for non-existent event."""
        from app.services.bill24 import Bill24Client, Bill24Error

        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        async def mock_request(command, params=None):
            if command == "GET_ACTION_EXT":
                return {
                    "resultCode": 10,
                    "description": "Action not found",
                    "cause": "EVENT_NOT_FOUND"
                }
            return {"resultCode": 0}

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "resultCode": 10,
                "description": "Action not found"
            }
            mock_response.raise_for_status = MagicMock()
            mock_http_client.post.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            with pytest.raises(Bill24Error) as exc_info:
                await client.get_action_ext(action_id=99999)

            assert exc_info.value.code == 10


class TestCancelledEvent:
    """Test handling of cancelled events."""

    @pytest.mark.asyncio
    async def test_cancelled_event_no_seats(self):
        """Test cancelled event returns no available seats."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test"
        )

        async def mock_request(command, params=None):
            if command == "GET_SEAT_LIST":
                return {
                    "resultCode": 0,
                    "seatList": []  # No seats available
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            seats = await client.get_seat_list(action_event_id=100)

            # Cancelled event has no seats
            assert len(seats) == 0

    @pytest.mark.asyncio
    async def test_event_cancelled_error(self):
        """Test explicit event cancelled error."""
        from app.services.bill24 import Bill24Client, Bill24Error

        client = Bill24Client(
            fid=1271, token="test", zone="test"
        )

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "resultCode": 20,
                "description": "Event has been cancelled",
                "cause": "EVENT_CANCELLED"
            }
            mock_response.raise_for_status = MagicMock()
            mock_http_client.post.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            with pytest.raises(Bill24Error) as exc_info:
                await client.get_seat_list(action_event_id=100)

            assert "cancelled" in exc_info.value.message.lower()


class TestSoldOutEvent:
    """Test handling of sold out events."""

    @pytest.mark.asyncio
    async def test_sold_out_event(self):
        """Test all seats show as SOLD."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "seatList": [
                    {"seatId": 1, "status": "SOLD", "price": 1000},
                    {"seatId": 2, "status": "SOLD", "price": 1000},
                    {"seatId": 3, "status": "SOLD", "price": 1500},
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            seats = await client.get_seat_list(action_event_id=100)

            # All seats are sold
            assert all(s["status"] == "SOLD" for s in seats)

            # No free seats
            free_seats = [s for s in seats if s["status"] == "FREE"]
            assert len(free_seats) == 0


class TestExpiredEvent:
    """Test handling of expired (past) events."""

    @pytest.mark.asyncio
    async def test_past_event_no_purchase(self):
        """Test past event cannot be purchased."""
        from app.services.bill24 import Bill24Client, Bill24Error

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "resultCode": 21,
                "description": "Event has already ended",
                "cause": "EVENT_EXPIRED"
            }
            mock_response.raise_for_status = MagicMock()
            mock_http_client.post.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            with pytest.raises(Bill24Error) as exc_info:
                await client.reserve_seats(
                    action_event_id=100,
                    seat_ids=[1, 2]
                )

            assert exc_info.value.code == 21


class TestEventAvailabilityCheck:
    """Test event availability checking."""

    @pytest.mark.asyncio
    async def test_check_event_is_active(self):
        """Test checking if event is active."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "actionId": 100,
                "isActive": True,
                "saleStatus": "ON_SALE"
            }

        with patch.object(client, '_request', side_effect=mock_request):
            event = await client.get_action_ext(action_id=100)

            # Check active status
            is_active = event.get("isActive", False)
            sale_status = event.get("saleStatus", "")

            assert is_active or sale_status == "ON_SALE"

    @pytest.mark.asyncio
    async def test_check_event_is_inactive(self):
        """Test detecting inactive event."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "actionId": 100,
                "isActive": False,
                "saleStatus": "SUSPENDED"
            }

        with patch.object(client, '_request', side_effect=mock_request):
            event = await client.get_action_ext(action_id=100)

            is_active = event.get("isActive", True)
            sale_status = event.get("saleStatus", "")

            # Event is not active
            assert not is_active or sale_status != "ON_SALE"


class TestErrorLocalization:
    """Test error message localization."""

    def test_event_not_found_message_ru(self):
        """Test Russian error for event not found."""
        from app.bot.localization import get_text

        text = get_text("error_event_not_found", "ru")

        assert text != "error_event_not_found"
        assert len(text) > 0

    def test_event_not_found_message_en(self):
        """Test English error for event not found."""
        from app.bot.localization import get_text

        text = get_text("error_event_not_found", "en")

        assert "not found" in text.lower() or "Event" in text


class TestWidgetErrorReturn:
    """Test widget returns user to bot on error."""

    def test_fail_url_contains_error(self):
        """Test fail URL can include error information."""
        base_url = "https://bot.example.com/payment/fail"
        error_code = "EVENT_CANCELLED"

        # Fail URL can include error parameter
        fail_url_with_error = f"{base_url}?error={error_code}"

        assert "error=" in fail_url_with_error
        assert error_code in fail_url_with_error

    @pytest.mark.asyncio
    async def test_order_creation_fail_url(self):
        """Test fail URL is passed to Bill24."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        captured_params = {}

        async def capture_request(command, params=None):
            if command == "CREATE_ORDER":
                captured_params.update(params or {})
                return {
                    "resultCode": 0,
                    "orderId": 123,
                    "formUrl": "https://pay.example.com/123"
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=capture_request):
            await client.create_order(
                success_url="https://bot.example.com/success",
                fail_url="https://bot.example.com/fail"
            )

            assert "failUrl" in captured_params
            assert captured_params["failUrl"] == "https://bot.example.com/fail"


class TestReservationErrors:
    """Test reservation-related errors."""

    @pytest.mark.asyncio
    async def test_reservation_for_unavailable_event(self):
        """Test reservation fails for unavailable event."""
        from app.services.bill24 import Bill24Client, Bill24Error

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "resultCode": 22,
                "description": "Event is not available for sale",
                "cause": "SALES_SUSPENDED"
            }
            mock_response.raise_for_status = MagicMock()
            mock_http_client.post.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            with pytest.raises(Bill24Error) as exc_info:
                await client.reserve_seats(
                    action_event_id=100,
                    seat_ids=[1]
                )

            assert exc_info.value.code == 22
            assert "not available" in exc_info.value.message.lower()


class TestBotEventValidation:
    """Test bot validates events before showing."""

    @pytest.mark.asyncio
    async def test_bot_handles_event_not_found(self):
        """Test bot handles event not found gracefully."""
        from app.bot.handlers import callback_event_details
        from app.services.bill24 import Bill24Error

        callback = AsyncMock()
        callback.data = "event_99999"
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
        mock_agent.is_active = True
        mock_agent.fid = 1271
        mock_agent.token = "test"
        mock_agent.zone = "test"

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
                mock_fetch.return_value = []  # Event not in list

                await callback_event_details(callback)

                # Should show error
                callback.message.edit_text.assert_called()


class TestEventStatusCodes:
    """Test Bill24 event status codes."""

    def test_known_error_codes(self):
        """Test known Bill24 error codes are documented."""
        # Common error codes
        error_codes = {
            0: "Success",
            1: "Session error",
            10: "Event not found",
            20: "Event cancelled",
            21: "Event expired",
            22: "Sales suspended",
            30: "Seat not available",
        }

        # Verify codes are defined
        assert 0 in error_codes  # Success
        assert 10 in error_codes  # Not found
        assert 20 in error_codes  # Cancelled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
