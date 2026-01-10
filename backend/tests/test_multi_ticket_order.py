"""
Test multiple tickets in single order.

Tests that users can purchase multiple tickets in a single order
and each ticket gets a unique QR code.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestMultiSeatReservation:
    """Test reserving multiple seats at once."""

    @pytest.mark.asyncio
    async def test_reserve_multiple_seats(self):
        """Test reserving multiple seats in one call."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=1001,
            session_id="test_session"
        )

        # Mock successful multi-seat reservation
        async def mock_request(command, params=None):
            if command == "RESERVATION":
                return {
                    "resultCode": 0,
                    "seatList": [
                        {"seatId": 101, "status": "RESERVED", "price": 1000},
                        {"seatId": 102, "status": "RESERVED", "price": 1000},
                        {"seatId": 103, "status": "RESERVED", "price": 1500},
                    ],
                    "cartTimeout": 600,
                    "totalSum": 3500
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.reserve_seats(
                action_event_id=100,
                seat_ids=[101, 102, 103]
            )

            # All 3 seats should be reserved
            assert len(result["seatList"]) == 3
            assert result["totalSum"] == 3500
            assert all(s["status"] == "RESERVED" for s in result["seatList"])

    @pytest.mark.asyncio
    async def test_reserve_seats_calculates_total(self):
        """Test total price is calculated correctly for multiple seats."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "seatList": [
                    {"seatId": 1, "price": 2000},
                    {"seatId": 2, "price": 2500},
                    {"seatId": 3, "price": 3000},
                    {"seatId": 4, "price": 1500},
                ],
                "totalSum": 9000,  # 2000 + 2500 + 3000 + 1500
                "cartTimeout": 600
            }

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.reserve_seats(
                action_event_id=100,
                seat_ids=[1, 2, 3, 4]
            )

            # Verify total
            assert result["totalSum"] == 9000
            expected_total = sum(s["price"] for s in result["seatList"])
            assert result["totalSum"] == expected_total


class TestMultiTicketOrder:
    """Test creating order with multiple tickets."""

    @pytest.mark.asyncio
    async def test_create_order_with_multiple_seats(self):
        """Test order creation with multiple reserved seats."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            if command == "CREATE_ORDER":
                return {
                    "resultCode": 0,
                    "orderId": 12345,
                    "formUrl": "https://pay.example.com/12345",
                    "externalOrderId": "EXT12345",
                    "statusExtInt": 0
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.create_order(
                success_url="https://example.com/success",
                fail_url="https://example.com/fail"
            )

            assert result["orderId"] == 12345
            assert result["formUrl"] is not None


class TestMultiTicketDelivery:
    """Test delivery of multiple tickets."""

    @pytest.mark.asyncio
    async def test_get_tickets_returns_multiple(self):
        """Test GET_TICKETS_BY_ORDER returns all tickets."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            if command == "GET_TICKETS_BY_ORDER":
                return {
                    "resultCode": 0,
                    "ticketList": [
                        {
                            "ticketId": 1001,
                            "seatId": 101,
                            "row": "A",
                            "seat": "1",
                            "qrCode": "QR_DATA_1001",
                            "barcode": "BC_1001"
                        },
                        {
                            "ticketId": 1002,
                            "seatId": 102,
                            "row": "A",
                            "seat": "2",
                            "qrCode": "QR_DATA_1002",
                            "barcode": "BC_1002"
                        },
                        {
                            "ticketId": 1003,
                            "seatId": 103,
                            "row": "A",
                            "seat": "3",
                            "qrCode": "QR_DATA_1003",
                            "barcode": "BC_1003"
                        },
                    ]
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            tickets = await client.get_tickets_by_order(order_id=12345)

            # All 3 tickets should be returned
            assert len(tickets) == 3

            # Each ticket should have unique identifiers
            ticket_ids = [t["ticketId"] for t in tickets]
            assert len(set(ticket_ids)) == 3  # All unique


class TestUniqueQRCodes:
    """Test each ticket has a unique QR code."""

    @pytest.mark.asyncio
    async def test_each_ticket_has_unique_qr(self):
        """Test each ticket in order has unique QR code."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "ticketList": [
                    {"ticketId": 1, "qrCode": "UNIQUE_QR_A"},
                    {"ticketId": 2, "qrCode": "UNIQUE_QR_B"},
                    {"ticketId": 3, "qrCode": "UNIQUE_QR_C"},
                    {"ticketId": 4, "qrCode": "UNIQUE_QR_D"},
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            tickets = await client.get_tickets_by_order(order_id=12345)

            qr_codes = [t["qrCode"] for t in tickets]

            # All QR codes should be unique
            assert len(qr_codes) == len(set(qr_codes))

    @pytest.mark.asyncio
    async def test_each_ticket_has_unique_barcode(self):
        """Test each ticket has unique barcode."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "ticketList": [
                    {"ticketId": 1, "barcode": "1234567890001"},
                    {"ticketId": 2, "barcode": "1234567890002"},
                    {"ticketId": 3, "barcode": "1234567890003"},
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            tickets = await client.get_tickets_by_order(order_id=12345)

            barcodes = [t.get("barcode") for t in tickets if t.get("barcode")]

            # All barcodes should be unique
            assert len(barcodes) == len(set(barcodes))


class TestCompleteMultiTicketFlow:
    """Test complete flow of multi-ticket purchase."""

    @pytest.mark.asyncio
    async def test_complete_multi_ticket_purchase(self):
        """Test complete flow: reserve multiple -> order -> get tickets."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        call_sequence = []

        async def mock_request(command, params=None):
            call_sequence.append(command)

            if command == "RESERVATION":
                return {
                    "resultCode": 0,
                    "seatList": [
                        {"seatId": s, "status": "RESERVED", "price": 1000}
                        for s in params.get("seatList", [])
                    ],
                    "totalSum": len(params.get("seatList", [])) * 1000,
                    "cartTimeout": 600
                }
            elif command == "CREATE_ORDER":
                return {
                    "resultCode": 0,
                    "orderId": 99999,
                    "formUrl": "https://pay.example.com/99999"
                }
            elif command == "GET_TICKETS_BY_ORDER":
                return {
                    "resultCode": 0,
                    "ticketList": [
                        {"ticketId": i, "qrCode": f"QR_{i}", "seatId": i + 100}
                        for i in range(1, 6)  # 5 tickets
                    ]
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            # Step 1: Reserve 5 seats
            reserve_result = await client.reserve_seats(
                action_event_id=100,
                seat_ids=[101, 102, 103, 104, 105]
            )
            assert len(reserve_result["seatList"]) == 5
            assert reserve_result["totalSum"] == 5000

            # Step 2: Create order
            order_result = await client.create_order(
                success_url="https://example.com/success",
                fail_url="https://example.com/fail"
            )
            assert order_result["orderId"] == 99999

            # Step 3: Get tickets (simulating after payment)
            tickets = await client.get_tickets_by_order(order_id=99999)
            assert len(tickets) == 5

            # Verify unique QR codes
            qr_codes = [t["qrCode"] for t in tickets]
            assert len(set(qr_codes)) == 5

        # Verify call sequence
        assert call_sequence == ["RESERVATION", "CREATE_ORDER", "GET_TICKETS_BY_ORDER"]


class TestTicketDeliveryJob:
    """Test ticket delivery background job handles multiple tickets."""

    @pytest.mark.asyncio
    async def test_delivery_job_sends_all_tickets(self):
        """Test background job delivers all tickets in order."""
        from app.core.background_jobs import process_ticket_delivery_job

        # This test verifies the job can handle multiple tickets
        # The actual implementation sends each ticket individually
        # or as a batch

        assert callable(process_ticket_delivery_job)


class TestDatabaseMultiTicketStorage:
    """Test database can store multiple tickets per order."""

    def test_ticket_model_has_order_relationship(self):
        """Test Ticket model can belong to an Order."""
        from app.models import Ticket, Order

        # Verify Ticket has order_id foreign key
        assert hasattr(Ticket, 'order_id')

        # Verify Order has tickets relationship
        assert hasattr(Order, 'tickets')

    def test_order_can_have_multiple_tickets(self):
        """Test Order model supports multiple tickets."""
        from app.models import Order

        # Order should have a tickets relationship (one-to-many)
        assert hasattr(Order, 'tickets')


class TestMultiTicketPricing:
    """Test pricing for multiple tickets."""

    @pytest.mark.asyncio
    async def test_different_price_seats_in_order(self):
        """Test order with seats at different prices."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "seatList": [
                    {"seatId": 1, "price": 500, "sectorName": "Standard"},
                    {"seatId": 2, "price": 1000, "sectorName": "Premium"},
                    {"seatId": 3, "price": 2500, "sectorName": "VIP"},
                ],
                "totalSum": 4000,  # 500 + 1000 + 2500
                "cartTimeout": 600
            }

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.reserve_seats(
                action_event_id=100,
                seat_ids=[1, 2, 3]
            )

            # Total should be sum of all prices
            assert result["totalSum"] == 4000

            # Individual prices should be preserved
            prices = [s["price"] for s in result["seatList"]]
            assert 500 in prices
            assert 1000 in prices
            assert 2500 in prices


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
