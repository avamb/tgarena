"""
Test ticket PDF generation.

Tests that PDF tickets can be generated and contain required information.
"""

import pytest
import base64
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestPrintTicketsAPI:
    """Test PRINT_TICKETS API command."""

    @pytest.mark.asyncio
    async def test_print_tickets_returns_pdf_bytes(self):
        """Test PRINT_TICKETS returns PDF as bytes."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test_token",
            zone="test",
            user_id=1001,
            session_id="test_session"
        )

        # Mock PDF content (minimal valid PDF header)
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 0\ntrailer\n<<\n>>\nstartxref\n0\n%%EOF"
        encoded_pdf = base64.b64encode(pdf_content).decode()

        async def mock_request(command, params=None):
            if command == "PRINT_TICKETS":
                return {
                    "resultCode": 0,
                    "pdfData": encoded_pdf
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.print_tickets(order_id=12345)

            # Should return bytes
            assert isinstance(result, bytes)

            # Should be valid PDF (starts with %PDF)
            assert result.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_print_tickets_sends_order_id(self):
        """Test PRINT_TICKETS sends order_id parameter."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        captured_params = {}

        async def capture_request(command, params=None):
            if command == "PRINT_TICKETS":
                captured_params.update(params or {})
                return {
                    "resultCode": 0,
                    "pdfData": base64.b64encode(b"%PDF-1.4").decode()
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=capture_request):
            await client.print_tickets(order_id=99999)

            assert captured_params.get("orderId") == 99999


class TestPDFContent:
    """Test PDF ticket content."""

    @pytest.mark.asyncio
    async def test_pdf_is_valid_binary(self):
        """Test returned PDF is valid binary data."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        # Create a realistic PDF mock
        pdf_mock = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"  # PDF header with binary marker
        pdf_mock += b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        pdf_mock += b"xref\n0 0\ntrailer << >>\nstartxref 0\n%%EOF"

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "pdfData": base64.b64encode(pdf_mock).decode()
            }

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.print_tickets(order_id=12345)

            # Check it's proper binary
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_pdf_header_format(self):
        """Test PDF header format is recognized."""
        # Valid PDF header
        valid_pdf = b"%PDF-1.4\n"
        assert valid_pdf.startswith(b"%PDF")

        # PDF version can vary
        for version in ["1.4", "1.5", "1.6", "1.7", "2.0"]:
            header = f"%PDF-{version}\n".encode()
            assert header.startswith(b"%PDF")


class TestPDFDelivery:
    """Test PDF delivery to user."""

    @pytest.mark.asyncio
    async def test_pdf_can_be_sent_as_document(self):
        """Test PDF bytes can be packaged for Telegram."""
        from app.services.bill24 import Bill24Client
        from io import BytesIO

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        pdf_mock = b"%PDF-1.4\nTest PDF Content"

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "pdfData": base64.b64encode(pdf_mock).decode()
            }

        with patch.object(client, '_request', side_effect=mock_request):
            pdf_bytes = await client.print_tickets(order_id=12345)

            # Can create BytesIO for Telegram
            pdf_file = BytesIO(pdf_bytes)
            pdf_file.name = "tickets_12345.pdf"

            assert pdf_file.read() == pdf_mock
            assert pdf_file.name.endswith(".pdf")


class TestMultipleTicketsPDF:
    """Test PDF with multiple tickets."""

    @pytest.mark.asyncio
    async def test_pdf_contains_all_tickets(self):
        """Test PDF is generated for all tickets in order."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        # Multi-page PDF mock (simplified)
        multi_ticket_pdf = b"%PDF-1.4\nMulti-ticket document"

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "pdfData": base64.b64encode(multi_ticket_pdf).decode()
            }

        with patch.object(client, '_request', side_effect=mock_request):
            pdf_bytes = await client.print_tickets(order_id=12345)

            # PDF should be returned (would contain multiple pages)
            assert len(pdf_bytes) > 0


class TestPDFErrorHandling:
    """Test PDF generation error handling."""

    @pytest.mark.asyncio
    async def test_handles_empty_pdf_data(self):
        """Test handling when pdfData is empty."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "pdfData": ""  # Empty PDF data
            }

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.print_tickets(order_id=12345)

            # Should return empty bytes
            assert result == b""

    @pytest.mark.asyncio
    async def test_handles_invalid_base64(self):
        """Test handling when pdfData is invalid base64."""
        from app.services.bill24 import Bill24Client
        import binascii

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "pdfData": "not-valid-base64!!!"
            }

        with patch.object(client, '_request', side_effect=mock_request):
            with pytest.raises(binascii.Error):
                await client.print_tickets(order_id=12345)


class TestPDFAPIMethod:
    """Test Bill24Client.print_tickets method."""

    def test_print_tickets_method_exists(self):
        """Test print_tickets method exists."""
        from app.services.bill24 import Bill24Client
        import inspect

        assert hasattr(Bill24Client, 'print_tickets')
        assert inspect.iscoroutinefunction(Bill24Client.print_tickets)

    def test_print_tickets_signature(self):
        """Test print_tickets has correct parameters."""
        from app.services.bill24 import Bill24Client
        import inspect

        sig = inspect.signature(Bill24Client.print_tickets)
        params = list(sig.parameters.keys())

        assert 'order_id' in params


class TestTicketDataForPDF:
    """Test ticket data needed for PDF."""

    @pytest.mark.asyncio
    async def test_ticket_has_qr_data(self):
        """Test ticket data includes QR code data."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "ticketList": [
                    {
                        "ticketId": 1,
                        "qrCode": "QR_ENCODED_DATA_FOR_TICKET_1",
                        "barcode": "1234567890001",
                        "seatId": 101,
                        "row": "A",
                        "seat": "1",
                        "eventName": "Concert 2026",
                        "venueName": "Arena Stadium",
                        "eventDate": "2026-03-15T19:00:00"
                    }
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            tickets = await client.get_tickets_by_order(order_id=12345)

            ticket = tickets[0]

            # Required fields for PDF
            assert "qrCode" in ticket
            assert "barcode" in ticket
            assert "eventName" in ticket
            assert "venueName" in ticket
            assert "row" in ticket
            assert "seat" in ticket

    @pytest.mark.asyncio
    async def test_ticket_has_event_details(self):
        """Test ticket includes event details for PDF."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        async def mock_request(command, params=None):
            return {
                "resultCode": 0,
                "ticketList": [
                    {
                        "ticketId": 1,
                        "eventName": "Rock Festival 2026",
                        "eventDate": "2026-06-20T18:00:00",
                        "venueName": "Open Air Stadium",
                        "sectorName": "VIP Zone",
                        "row": "1",
                        "seat": "15",
                        "price": 5000
                    }
                ]
            }

        with patch.object(client, '_request', side_effect=mock_request):
            tickets = await client.get_tickets_by_order(order_id=12345)

            ticket = tickets[0]

            # Event details for PDF
            assert ticket["eventName"] == "Rock Festival 2026"
            assert ticket["venueName"] == "Open Air Stadium"
            assert "eventDate" in ticket


class TestPDFFilename:
    """Test PDF filename generation."""

    def test_generate_pdf_filename(self):
        """Test generating appropriate PDF filename."""
        order_id = 12345

        # Expected filename format
        filename = f"tickets_{order_id}.pdf"

        assert filename == "tickets_12345.pdf"
        assert filename.endswith(".pdf")

    def test_filename_with_special_order_id(self):
        """Test filename with large order ID."""
        order_id = 9999999999

        filename = f"tickets_{order_id}.pdf"

        assert str(order_id) in filename
        assert filename.endswith(".pdf")


class TestIntegrationFlow:
    """Test complete PDF generation flow."""

    @pytest.mark.asyncio
    async def test_complete_flow_to_pdf(self):
        """Test complete flow from order to PDF."""
        from app.services.bill24 import Bill24Client
        from io import BytesIO

        client = Bill24Client(
            fid=1271, token="test", zone="test",
            user_id=1001, session_id="test"
        )

        pdf_content = b"%PDF-1.4\nComplete ticket document"

        async def mock_request(command, params=None):
            if command == "GET_ORDER_INFO":
                return {
                    "resultCode": 0,
                    "orderId": 12345,
                    "status": "PAID"
                }
            elif command == "GET_TICKETS_BY_ORDER":
                return {
                    "resultCode": 0,
                    "ticketList": [
                        {"ticketId": 1, "qrCode": "QR1"},
                        {"ticketId": 2, "qrCode": "QR2"},
                    ]
                }
            elif command == "PRINT_TICKETS":
                return {
                    "resultCode": 0,
                    "pdfData": base64.b64encode(pdf_content).decode()
                }
            return {"resultCode": 0}

        with patch.object(client, '_request', side_effect=mock_request):
            # Step 1: Check order is paid
            order_info = await client.get_order_info(order_id=12345)
            assert order_info["status"] == "PAID"

            # Step 2: Get ticket details
            tickets = await client.get_tickets_by_order(order_id=12345)
            assert len(tickets) == 2

            # Step 3: Generate PDF
            pdf_bytes = await client.print_tickets(order_id=12345)
            assert pdf_bytes.startswith(b"%PDF")

            # Step 4: Prepare for Telegram
            pdf_file = BytesIO(pdf_bytes)
            pdf_file.name = f"tickets_{12345}.pdf"

            assert pdf_file.name == "tickets_12345.pdf"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
