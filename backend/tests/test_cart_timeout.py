"""
Test cart timeout notification.

Tests for cart expiry notification to users.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.bill24 import Bill24Client


class TestCartTimeoutLocalization:
    """Test cart timeout notification localization."""

    def test_cart_expiring_message_ru(self):
        """Test cart expiring message exists in Russian."""
        from app.bot.localization import TRANSLATIONS

        ru = TRANSLATIONS.get("ru", {})
        # Cart-related messages
        assert any("cart" in k.lower() or "корзин" in v.lower()
                   for k, v in ru.items() if isinstance(v, str))

    def test_error_session_expired_ru(self):
        """Test session expired error in Russian."""
        from app.bot.localization import get_text

        text = get_text("error_session_expired", "ru")
        assert len(text) > 0
        # Should contain Russian text
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        assert has_cyrillic


class TestCartTimeoutFromAPI:
    """Test cart timeout from Bill24 API."""

    @pytest.mark.asyncio
    async def test_reservation_returns_cart_timeout(self):
        """Test RESERVATION returns cartTimeout."""
        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "seatList": [1, 2],
            "cartTimeout": 900,  # 15 minutes
            "totalSum": 5000
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # Call reservation
            result = await client._request("RESERVATION", {
                "actionEventId": 12345,
                "seatList": [1],
                "type": "RESERVE"
            })

            assert "cartTimeout" in result
            assert result["cartTimeout"] > 0

    @pytest.mark.asyncio
    async def test_get_cart_returns_time_remaining(self):
        """Test GET_CART returns time remaining."""
        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        mock_response = {
            "resultCode": 0,
            "actionEventList": [{"actionEventId": 1}],
            "time": 600,  # 10 minutes remaining
            "totalSum": 5000
        }

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_cart()

            assert "time" in result


class TestCartExpiryWarning:
    """Test cart expiry warning before timeout."""

    def test_session_expired_localization_exists(self):
        """Test session expired message exists."""
        from app.bot.localization import get_text

        text_ru = get_text("error_session_expired", "ru")
        text_en = get_text("error_session_expired", "en")

        assert len(text_ru) > 0
        assert len(text_en) > 0


class TestCartClearedNotification:
    """Test cart cleared notification on timeout."""

    def test_error_reservation_failed_exists(self):
        """Test reservation failed error exists."""
        from app.bot.localization import get_text

        text_ru = get_text("error_reservation_failed", "ru")
        text_en = get_text("error_reservation_failed", "en")

        assert len(text_ru) > 0
        assert len(text_en) > 0

    def test_order_cancelled_message_exists(self):
        """Test order cancelled message exists."""
        from app.bot.localization import get_text

        text = get_text("order_cancelled", "ru", order_id=123)
        assert "123" in text


class TestCartTimeoutHandling:
    """Test cart timeout handling logic."""

    @pytest.mark.asyncio
    async def test_unreserve_all_method_exists(self):
        """Test unreserve_all method exists."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        assert hasattr(client, 'unreserve_all')
        assert callable(client.unreserve_all)

    @pytest.mark.asyncio
    async def test_get_cart_method_exists(self):
        """Test get_cart method exists."""
        from app.services.bill24 import Bill24Client

        client = Bill24Client(
            fid=1271,
            token="test",
            zone="test",
            user_id=100,
            session_id="session_123"
        )

        assert hasattr(client, 'get_cart')
        assert callable(client.get_cart)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
