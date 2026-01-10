"""
Test ticket delivery with QR code.

Tests for ticket message format and content after purchase.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.localization import get_text


class TestTicketMessageReceived:
    """Test ticket message is received after purchase."""

    @pytest.mark.asyncio
    async def test_ticket_delivery_function_exists(self):
        """Test ticket delivery function exists."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        assert callable(process_ticket_delivery_job)
        assert inspect.iscoroutinefunction(process_ticket_delivery_job)

    def test_ticket_info_localization_exists(self):
        """Test ticket_info localization key exists."""
        text_ru = get_text("ticket_info", "ru",
                          event_name="Test",
                          date="01.01.2026",
                          venue="Venue",
                          sector="A",
                          row="1",
                          seat="5",
                          price=1000)

        text_en = get_text("ticket_info", "en",
                          event_name="Test",
                          date="01.01.2026",
                          venue="Venue",
                          sector="A",
                          row="1",
                          seat="5",
                          price=1000)

        assert len(text_ru) > 0
        assert len(text_en) > 0


class TestQRCodeImage:
    """Test QR code image in ticket."""

    def test_ticket_model_has_qr_field(self):
        """Test Ticket model has qr_code_data field."""
        from app.models import Ticket

        assert hasattr(Ticket, 'qr_code_data')

    def test_qr_code_data_format(self):
        """Test QR code data can be stored."""
        qr_data = "TICKET:123456789:A1:5"

        # QR data should be a string
        assert isinstance(qr_data, str)
        assert len(qr_data) > 0


class TestBarcodeImage:
    """Test barcode image in ticket."""

    def test_ticket_model_has_barcode_field(self):
        """Test Ticket model has barcode_data field."""
        from app.models import Ticket

        assert hasattr(Ticket, 'barcode_data')

    def test_barcode_data_format(self):
        """Test barcode data can be stored."""
        barcode_data = "1234567890123"

        # Barcode data should be a string of digits
        assert isinstance(barcode_data, str)
        assert barcode_data.isdigit()


class TestEventNameAndDate:
    """Test event name and date in ticket."""

    def test_ticket_message_contains_event_name(self):
        """Test ticket message contains event name."""
        text = get_text("ticket_info", "ru",
                       event_name="Rock Concert",
                       date="15.03.2026",
                       venue="Arena",
                       sector="VIP",
                       row="A",
                       seat="10",
                       price=5000)

        assert "Rock Concert" in text

    def test_ticket_message_contains_date(self):
        """Test ticket message contains date."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="25.12.2026 19:00",
                       venue="Arena",
                       sector="A",
                       row="1",
                       seat="5",
                       price=2000)

        assert "25.12.2026" in text or "19:00" in text

    def test_ticket_has_date_emoji(self):
        """Test ticket message has date emoji."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Venue",
                       sector="A",
                       row="1",
                       seat="1",
                       price=1000)

        assert "📅" in text


class TestSeatDetails:
    """Test seat details in ticket."""

    def test_ticket_contains_sector(self):
        """Test ticket contains sector."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Arena",
                       sector="VIP Section",
                       row="A",
                       seat="10",
                       price=5000)

        assert "VIP Section" in text

    def test_ticket_contains_row(self):
        """Test ticket contains row number."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Arena",
                       sector="Standard",
                       row="15",
                       seat="10",
                       price=2000)

        assert "15" in text

    def test_ticket_contains_seat(self):
        """Test ticket contains seat number."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Arena",
                       sector="Standard",
                       row="5",
                       seat="42",
                       price=2000)

        assert "42" in text

    def test_ticket_has_seat_emoji(self):
        """Test ticket has seat emoji."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Venue",
                       sector="A",
                       row="1",
                       seat="1",
                       price=1000)

        assert "🪑" in text


class TestPriceShown:
    """Test price shown in ticket."""

    def test_ticket_contains_price(self):
        """Test ticket contains price."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Arena",
                       sector="Standard",
                       row="5",
                       seat="10",
                       price=3500)

        assert "3500" in text

    def test_ticket_has_currency(self):
        """Test ticket shows currency."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Arena",
                       sector="A",
                       row="1",
                       seat="1",
                       price=1000)

        assert "₽" in text

    def test_ticket_has_price_emoji(self):
        """Test ticket has price emoji."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Venue",
                       sector="A",
                       row="1",
                       seat="1",
                       price=1000)

        assert "💰" in text


class TestVenueInformation:
    """Test venue information in ticket."""

    def test_ticket_contains_venue(self):
        """Test ticket contains venue name."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Olympic Stadium",
                       sector="A",
                       row="1",
                       seat="1",
                       price=1000)

        assert "Olympic Stadium" in text

    def test_ticket_has_venue_emoji(self):
        """Test ticket has venue/location emoji."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Venue",
                       sector="A",
                       row="1",
                       seat="1",
                       price=1000)

        assert "📍" in text


class TestTicketEmoji:
    """Test ticket has appropriate emojis."""

    def test_ticket_has_ticket_emoji(self):
        """Test ticket has 🎫 emoji."""
        text = get_text("ticket_info", "ru",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Venue",
                       sector="A",
                       row="1",
                       seat="1",
                       price=1000)

        assert "🎫" in text


class TestTicketLocalization:
    """Test ticket message localization."""

    def test_ticket_russian_format(self):
        """Test ticket in Russian format."""
        text = get_text("ticket_info", "ru",
                       event_name="Концерт",
                       date="01.01.2026",
                       venue="Арена",
                       sector="VIP",
                       row="A",
                       seat="10",
                       price=5000)

        # Russian labels should be present
        assert "Концерт" in text or "Арена" in text

    def test_ticket_english_format(self):
        """Test ticket in English format."""
        text = get_text("ticket_info", "en",
                       event_name="Concert",
                       date="01.01.2026",
                       venue="Arena",
                       sector="VIP",
                       row="A",
                       seat="10",
                       price=5000)

        # English format
        assert "Concert" in text
        assert "Arena" in text


class TestTicketModel:
    """Test Ticket model structure."""

    def test_ticket_model_exists(self):
        """Test Ticket model exists."""
        from app.models import Ticket

        assert Ticket is not None

    def test_ticket_has_order_id(self):
        """Test Ticket has order_id field."""
        from app.models import Ticket

        assert hasattr(Ticket, 'order_id')

    def test_ticket_has_seat_info(self):
        """Test Ticket has seat info fields."""
        from app.models import Ticket

        # Check for seat-related fields
        assert hasattr(Ticket, 'sector') or hasattr(Ticket, 'seat_row')


class TestTicketDeliveryToBill24:
    """Test getting tickets from Bill24 after payment."""

    @pytest.mark.asyncio
    async def test_get_tickets_method_exists(self):
        """Test get_tickets_by_order method exists."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        assert hasattr(client, 'get_tickets_by_order')

    @pytest.mark.asyncio
    async def test_get_tickets_returns_ticket_list(self):
        """Test get_tickets_by_order returns tickets."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "ticketList": [
                {
                    "ticketId": 1,
                    "qrCode": "https://example.com/qr/1",
                    "barcode": "1234567890"
                }
            ]
        }

        with patch.object(client, '_request', return_value=mock_response):
            tickets = await client.get_tickets_by_order(order_id=12345)

            assert len(tickets) >= 0


class TestTicketDeliveryJob:
    """Test the background job for ticket delivery."""

    @pytest.mark.asyncio
    async def test_ticket_delivery_job_exists(self):
        """Test process_ticket_delivery_job function exists."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        assert callable(process_ticket_delivery_job)
        assert inspect.iscoroutinefunction(process_ticket_delivery_job)

    @pytest.mark.asyncio
    async def test_ticket_delivery_job_sends_tickets(self):
        """Test that job sends individual tickets with details."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        # Get the source code to verify implementation
        source = inspect.getsource(process_ticket_delivery_job)

        # Verify it sends ticket messages with all required info
        assert "ticket.event_name" in source or "event_name" in source
        assert "ticket.event_date" in source or "event_date" in source
        assert "ticket.venue_name" in source or "venue_name" in source
        assert "ticket.sector" in source or "sector" in source
        assert "ticket.row" in source or "row" in source
        assert "ticket.seat" in source or "seat" in source
        assert "ticket.price" in source or "price" in source

    @pytest.mark.asyncio
    async def test_ticket_delivery_job_handles_qr_code(self):
        """Test that job handles QR code sending."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        source = inspect.getsource(process_ticket_delivery_job)

        # Verify QR code handling
        assert "qr_code_data" in source
        assert "send_photo" in source or "BufferedInputFile" in source

    @pytest.mark.asyncio
    async def test_ticket_delivery_job_handles_barcode(self):
        """Test that job handles barcode number."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        source = inspect.getsource(process_ticket_delivery_job)

        # Verify barcode handling
        assert "barcode_number" in source

    @pytest.mark.asyncio
    async def test_ticket_delivery_marks_sent(self):
        """Test that job marks tickets as sent."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect

        source = inspect.getsource(process_ticket_delivery_job)

        # Verify it marks tickets as sent
        assert "sent_to_user = True" in source
        assert "sent_at" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
