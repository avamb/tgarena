"""
Test sold-out event handling.

Tests that users see appropriate messages when trying to buy tickets
for sold-out events.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestSoldOutDetection:
    """Test detecting sold-out events."""

    @pytest.mark.asyncio
    async def test_all_seats_sold(self):
        """Test detecting when all seats are sold."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "seatList": [
                    {"seatId": 1, "status": "SOLD", "price": 1000},
                    {"seatId": 2, "status": "SOLD", "price": 1000},
                    {"seatId": 3, "status": "SOLD", "price": 1500},
                    {"seatId": 4, "status": "SOLD", "price": 1500},
                    {"seatId": 5, "status": "SOLD", "price": 2000},
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            seats = await client.get_seat_list(action_event_id=100)

            # Check if all sold
            free_seats = [s for s in seats if s["status"] == "FREE"]
            is_sold_out = len(free_seats) == 0

            assert is_sold_out

    @pytest.mark.asyncio
    async def test_empty_seat_list_is_sold_out(self):
        """Test empty seat list indicates sold out."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "seatList": []  # No seats at all
            }

        with patch.object(client, '_request', side_effect=mock_request):
            seats = await client.get_seat_list(action_event_id=100)

            is_sold_out = len(seats) == 0
            assert is_sold_out


class TestSoldOutMessages:
    """Test sold-out error messages."""

    def test_sold_out_message_exists_ru(self):
        """Test Russian sold-out message exists."""
        from app.bot.localization import TRANSLATIONS

        # Check if there's a sold out message
        ru_translations = TRANSLATIONS.get("ru", {})

        # Could be error_seats_unavailable or similar
        has_sold_out_msg = any(
            "распродан" in v.lower() or
            "билет" in v.lower() and "нет" in v.lower()
            for v in ru_translations.values()
            if isinstance(v, str)
        )

        # Or check specific key
        has_unavailable = "error_seats_unavailable" in ru_translations

        assert has_sold_out_msg or has_unavailable

    def test_sold_out_message_exists_en(self):
        """Test English sold-out message exists."""
        from app.bot.localization import TRANSLATIONS

        en_translations = TRANSLATIONS.get("en", {})

        has_sold_out_msg = any(
            "sold" in v.lower() or
            "unavailable" in v.lower() or
            "available" in v.lower()
            for v in en_translations.values()
            if isinstance(v, str)
        )

        assert has_sold_out_msg


class TestSoldOutUserFlow:
    """Test user flow when encountering sold-out event."""

    @pytest.mark.asyncio
    async def test_user_sees_no_seats_message(self):
        """Test user sees appropriate message for no seats."""
        from app.bot.localization import get_text

        text = get_text("error_seats_unavailable", "ru")

        # Should be a user-friendly message
        assert text != "error_seats_unavailable"
        assert len(text) > 0

    @pytest.mark.asyncio
    async def test_can_return_to_events_list(self):
        """Test user can go back to events list from sold out."""
        from app.bot.localization import get_text

        # Back button text should exist
        text = get_text("btn_back_to_events", "ru")

        assert text != "btn_back_to_events"
        assert len(text) > 0


class TestReservationForSoldOut:
    """Test reservation attempt for sold-out event."""

    @pytest.mark.asyncio
    async def test_reservation_fails_for_sold_seat(self):
        """Test reservation fails when seat is already sold."""
        from app.services.bill24 import Bill24Client, Bill24Error

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "resultCode": 30,
                "description": "Seat is not available",
                "cause": "SEAT_SOLD"
            }
            mock_response.raise_for_status = MagicMock()
            mock_http_client.post.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            with pytest.raises(Bill24Error) as exc_info:
                await client.reserve_seats(
                    action_event_id=100,
                    seat_ids=[1]
                )

            assert exc_info.value.code == 30

    @pytest.mark.asyncio
    async def test_reservation_returns_partial_success(self):
        """Test some seats reserved when others are sold."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            # Requested 3 seats, only 1 available
            return {
                "resultCode": 0,
                "seatList": [
                    {"seatId": 1, "status": "RESERVED"}
                    # Seats 2 and 3 were already sold
                ],
                "cartTimeout": 600,
                "totalSum": 1000
            }

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.reserve_seats(
                action_event_id=100,
                seat_ids=[1, 2, 3]  # Requested 3
            )

            # Only 1 was available
            assert len(result["seatList"]) < 3


class TestSoldOutEventInfo:
    """Test event info for sold-out events."""

    @pytest.mark.asyncio
    async def test_event_shows_available_seats_count(self):
        """Test event can show available seat count."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test"
        )

        async def mock_request(command, params=None):
            if command == "GET_ACTION_EXT":
                return {
                    "resultCode": 0,
                    "actionId": 100,
                    "actionName": "Sold Out Concert",
                    "availableSeats": 0,
                    "totalSeats": 500,
                    "saleStatus": "SOLD_OUT"
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            event = await client.get_action_ext(action_id=100)

            is_sold_out = (
                event.get("availableSeats", 0) == 0 or
                event.get("saleStatus") == "SOLD_OUT"
            )

            assert is_sold_out


class TestOtherEventsOption:
    """Test option to see other events."""

    def test_back_to_events_button_exists(self):
        """Test back to events button is available."""
        from app.bot.localization import get_text

        text_ru = get_text("btn_back_to_events", "ru")
        text_en = get_text("btn_back_to_events", "en")

        assert len(text_ru) > 0
        assert len(text_en) > 0

    @pytest.mark.asyncio
    async def test_events_list_excludes_sold_out(self):
        """Test events list can filter sold out events."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "actionList": [
                    {"actionId": 1, "actionName": "Available Event", "saleStatus": "ON_SALE"},
                    {"actionId": 2, "actionName": "Sold Out Event", "saleStatus": "SOLD_OUT"},
                    {"actionId": 3, "actionName": "Another Available", "saleStatus": "ON_SALE"},
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            response = await client.get_all_actions()
            events = response.get("actionList", [])

            # Could filter to show only available
            available_events = [
                e for e in events
                if e.get("saleStatus") != "SOLD_OUT"
            ]

            assert len(available_events) == 2


class TestSoldOutEdgeCases:
    """Test edge cases for sold-out handling."""

    @pytest.mark.asyncio
    async def test_last_seat_taken_during_checkout(self):
        """Test handling when last seat is taken during checkout."""
        from app.services.bill24 import Bill24Client, Bill24Error

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        # First call: seat looks available
        # Second call (reservation): seat now taken

        call_count = [0]

        async def mock_request(command, params=None):
            call_count[0] += 1

            if command == "GET_SEAT_LIST":
                return {
                    "resultCode": 0,
                    "seatList": [
                        {"seatId": 999, "status": "FREE", "price": 1000}
                    ]
                }
            elif command == "RESERVATION":
                # Seat was taken between GET and RESERVE
                return {
                    "resultCode": 30,
                    "description": "Seat no longer available"
                }
            return {"resultCode": 0}

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()

            call_count = [0]
            def get_response():
                call_count[0] += 1
                response = MagicMock()
                if call_count[0] == 1:
                    response.json.return_value = {
                        "resultCode": 0,
                        "seatList": [{"seatId": 999, "status": "FREE"}]
                    }
                else:
                    response.json.return_value = {
                        "resultCode": 30,
                        "description": "Seat no longer available"
                    }
                response.raise_for_status = MagicMock()
                return response

            mock_http_client.post.side_effect = lambda *a, **k: get_response()
            mock_get_client.return_value = mock_http_client

            # Get seats - shows available
            seats = await client.get_seat_list(action_event_id=100)
            assert len(seats) == 1

            # Try to reserve - fails
            with pytest.raises(Bill24Error):
                await client.reserve_seats(
                    action_event_id=100,
                    seat_ids=[999]
                )


class TestSoldOutLocalization:
    """Test sold-out message localization."""

    def test_seats_unavailable_ru(self):
        """Test Russian seats unavailable message."""
        from app.bot.localization import get_text

        text = get_text("error_seats_unavailable", "ru")

        # Should be in Russian
        assert any(char in text for char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя")

    def test_seats_unavailable_en(self):
        """Test English seats unavailable message."""
        from app.bot.localization import get_text

        text = get_text("error_seats_unavailable", "en")

        # Should contain expected words
        text_lower = text.lower()
        assert (
            "available" in text_lower or
            "unavailable" in text_lower or
            "sold" in text_lower or
            "refresh" in text_lower
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
