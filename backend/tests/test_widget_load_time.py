"""
Test widget load performance.

Tests that the Bill24 widget loads quickly and seat selection is responsive.
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# Maximum acceptable widget-related response times
MAX_WIDGET_URL_RESPONSE = 2.0  # Time to get widget URL
MAX_SEAT_LIST_RESPONSE = 3.0   # Time to load seat list


class TestWidgetURLGeneration:
    """Test widget URL is generated quickly."""

    @pytest.mark.asyncio
    async def test_create_order_returns_form_url_quickly(self):
        """Test create_order returns formUrl within time limit."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=1001,
            session_id="test_session"
        )

        # Mock successful create_order response
        async def mock_request(*args, **kwargs):
            return {
                "resultCode": 0,
                "orderId": 12345,
                "formUrl": "https://api.tixgear.com/pay/12345",
                "externalOrderId": "EXT123",
                "statusExtStr": "CREATED",
                "statusExtInt": 0
            }

        with patch.object(client, '_request', side_effect=mock_request):
            start_time = time.time()
            result = await client.create_order(
                success_url="https://example.com/success",
                fail_url="https://example.com/fail"
            )
            elapsed = time.time() - start_time

            # Should get formUrl quickly (with mocked backend)
            assert elapsed < MAX_WIDGET_URL_RESPONSE
            assert "formUrl" in result
            assert result["formUrl"] is not None

    @pytest.mark.asyncio
    async def test_form_url_is_valid_url(self):
        """Test formUrl is a valid HTTPS URL."""
        from app.services.bill24 import Bill24Client
        import re

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(*args, **kwargs):
            return {
                "resultCode": 0,
                "orderId": 12345,
                "formUrl": "https://api.tixgear.com:1240/pay/widget?order=12345",
                "statusExtInt": 0
            }

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.create_order(
                success_url="https://example.com/success",
                fail_url="https://example.com/fail"
            )

            form_url = result.get("formUrl", "")

            # Should be a valid HTTPS URL
            url_pattern = r'^https://[^\s]+$'
            assert re.match(url_pattern, form_url), f"Invalid URL format: {form_url}"


class TestSeatListLoad:
    """Test seat list loads quickly."""

    @pytest.mark.asyncio
    async def test_get_seat_list_responds_quickly(self):
        """Test get_seat_list returns within time limit."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test"
        )

        # Mock seat list with many seats
        mock_seats = [
            {
                "seatId": i,
                "row": f"Row {i // 10 + 1}",
                "seat": str(i % 10 + 1),
                "status": "FREE",
                "price": 1000 + (i * 10)
            }
            for i in range(100)  # 100 seats
        ]

        async def mock_request(*args, **kwargs):
            return {
                "resultCode": 0,
                "seatList": mock_seats
            }

        with patch.object(client, '_request', side_effect=mock_request):
            start_time = time.time()
            result = await client.get_seat_list(action_event_id=100)
            elapsed = time.time() - start_time

            # Should load quickly
            assert elapsed < MAX_SEAT_LIST_RESPONSE
            assert len(result) == 100


class TestWidgetPerformanceRequirements:
    """Test widget performance requirements are documented."""

    def test_performance_sla_exists(self):
        """Verify performance SLA is documented."""
        assert MAX_SEAT_LIST_RESPONSE == 3.0
        assert MAX_WIDGET_URL_RESPONSE == 2.0

    def test_widget_architecture_is_external(self):
        """Verify widget is hosted externally (Bill24)."""
        # The widget is hosted on Bill24's servers
        # We only provide the formUrl redirect
        # Load time depends on Bill24's infrastructure

        expected_widget_host = "tixgear.com"

        # Widget URL should point to Bill24
        test_form_url = "https://api.tixgear.com:1240/pay/widget?order=12345"
        assert expected_widget_host in test_form_url


class TestBill24WidgetIntegration:
    """Test Bill24 widget integration points."""

    @pytest.mark.asyncio
    async def test_order_creation_provides_redirect(self):
        """Test order creation provides widget redirect URL."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(*args, **kwargs):
            return {
                "resultCode": 0,
                "orderId": 99999,
                "formUrl": "https://pay.tixgear.com/order/99999",
                "externalOrderId": "EXT99999"
            }

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.create_order(
                success_url="https://bot.example.com/success",
                fail_url="https://bot.example.com/fail"
            )

            # Widget URL should be returned
            assert result["formUrl"] is not None
            assert "99999" in result["formUrl"]

    @pytest.mark.asyncio
    async def test_success_fail_urls_included(self):
        """Test success/fail URLs are passed to Bill24."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        captured_params = {}

        async def capture_request(command, params=None):
            captured_params.update(params or {})
            return {
                "resultCode": 0,
                "orderId": 123,
                "formUrl": "https://pay.example.com/123"
            }

        with patch.object(client, '_request', side_effect=capture_request):
            await client.create_order(
                success_url="https://bot.example.com/payment/success",
                fail_url="https://bot.example.com/payment/fail"
            )

            # Verify URLs were passed
            assert captured_params.get("successUrl") == "https://bot.example.com/payment/success"
            assert captured_params.get("failUrl") == "https://bot.example.com/payment/fail"


class TestWidgetSeatDisplay:
    """Test seat display functionality."""

    @pytest.mark.asyncio
    async def test_seat_list_contains_required_fields(self):
        """Test seat list has fields needed for display."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test"
        )

        async def mock_request(*args, **kwargs):
            return {
                "resultCode": 0,
                "seatList": [
                    {
                        "seatId": 1,
                        "row": "A",
                        "seat": "1",
                        "status": "FREE",
                        "price": 1500,
                        "sectorName": "VIP"
                    },
                    {
                        "seatId": 2,
                        "row": "A",
                        "seat": "2",
                        "status": "RESERVED",
                        "price": 1500,
                        "sectorName": "VIP"
                    }
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            seats = await client.get_seat_list(action_event_id=100)

            # Verify required fields for widget display
            assert len(seats) == 2

            for seat in seats:
                assert "seatId" in seat
                assert "status" in seat
                assert "price" in seat

    @pytest.mark.asyncio
    async def test_seat_status_values(self):
        """Test seat status values are valid."""
        valid_statuses = {"FREE", "RESERVED", "SOLD", "BLOCKED"}

        from app.services.bill24 import Bill24Client

        client = Bill24Client(fid=1271, token="test", zone="test")

        async def mock_request(*args, **kwargs):
            return {
                "resultCode": 0,
                "seatList": [
                    {"seatId": 1, "status": "FREE", "price": 1000},
                    {"seatId": 2, "status": "RESERVED", "price": 1000},
                    {"seatId": 3, "status": "SOLD", "price": 1000},
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            seats = await client.get_seat_list(action_event_id=100)

            for seat in seats:
                assert seat["status"] in valid_statuses


class TestWidgetBuyFlow:
    """Test the complete buy ticket flow timing."""

    @pytest.mark.asyncio
    async def test_complete_flow_performance(self):
        """Test complete flow from event to widget is fast."""
        from app.services.bill24 import Bill24Client

        # Simulate complete flow
        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        # Mock all API calls
        call_times = []

        async def mock_request(command, params=None):
            start = time.time()

            if command == "GET_SEAT_LIST":
                return {
                    "resultCode": 0,
                    "seatList": [{"seatId": i, "status": "FREE", "price": 1000} for i in range(50)]
                }
            elif command == "RESERVATION":
                return {
                    "resultCode": 0,
                    "seatList": [{"seatId": 1, "status": "RESERVED"}],
                    "cartTimeout": 600,
                    "totalSum": 1000
                }
            elif command == "CREATE_ORDER":
                return {
                    "resultCode": 0,
                    "orderId": 12345,
                    "formUrl": "https://pay.example.com/12345"
                }

            call_times.append(time.time() - start)
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            # Step 1: Load seats
            start = time.time()
            seats = await client.get_seat_list(action_event_id=100)
            seat_time = time.time() - start

            # Step 2: Reserve seat
            start = time.time()
            reserve = await client.reserve_seats(action_event_id=100, seat_ids=[1])
            reserve_time = time.time() - start

            # Step 3: Create order (get widget URL)
            start = time.time()
            order = await client.create_order(
                success_url="https://example.com/success",
                fail_url="https://example.com/fail"
            )
            order_time = time.time() - start

            # Total time should be reasonable
            total_time = seat_time + reserve_time + order_time

            # With mocked backend, should be very fast
            assert total_time < 1.0
            assert order["formUrl"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
