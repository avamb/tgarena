"""
Test order status notifications in bot.

Tests that order status changes trigger notifications to users.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.bot.localization import get_text


class TestOrderStatusLocalization:
    """Test order status notification localization strings."""

    def test_order_new_ru(self):
        """Test Russian new order notification."""
        text = get_text("order_new", "ru", order_id=123, amount=5000)
        assert "#123" in text
        assert "5000" in text
        assert "Заказ" in text

    def test_order_new_en(self):
        """Test English new order notification."""
        text = get_text("order_new", "en", order_id=456, amount=2500)
        assert "#456" in text
        assert "2500" in text
        assert "Order" in text

    def test_order_paid_ru(self):
        """Test Russian paid order notification."""
        text = get_text("order_paid", "ru", order_id=789, amount=3000)
        assert "#789" in text
        assert "3000" in text
        assert "оплачен" in text.lower()

    def test_order_paid_en(self):
        """Test English paid order notification."""
        text = get_text("order_paid", "en", order_id=101, amount=1000)
        assert "#101" in text
        assert "1000" in text
        assert "paid" in text.lower()

    def test_order_cancelled_ru(self):
        """Test Russian cancelled order notification."""
        text = get_text("order_cancelled", "ru", order_id=111)
        assert "#111" in text
        assert "отменён" in text.lower()

    def test_order_cancelled_en(self):
        """Test English cancelled order notification."""
        text = get_text("order_cancelled", "en", order_id=222)
        assert "#222" in text
        assert "cancelled" in text.lower()

    def test_order_refunded_ru(self):
        """Test Russian refund notification."""
        text = get_text("order_refunded", "ru", order_id=333, amount=4000)
        assert "#333" in text
        assert "4000" in text
        assert "возврат" in text.lower()

    def test_order_refunded_en(self):
        """Test English refund notification."""
        text = get_text("order_refunded", "en", order_id=444, amount=6000)
        assert "#444" in text
        assert "6000" in text
        assert "refund" in text.lower()


class TestOrderStatusContent:
    """Test order status notification content."""

    def test_new_order_has_amount(self):
        """Test new order notification includes amount."""
        text = get_text("order_new", "ru", order_id=1, amount=1500)
        assert "1500" in text
        assert "₽" in text

    def test_paid_order_has_ticket_notice(self):
        """Test paid order notification mentions tickets."""
        text_ru = get_text("order_paid", "ru", order_id=1, amount=1000)
        text_en = get_text("order_paid", "en", order_id=1, amount=1000)

        assert "билет" in text_ru.lower()
        assert "ticket" in text_en.lower()

    def test_status_notifications_have_emojis(self):
        """Test status notifications have appropriate emojis."""
        new_text = get_text("order_new", "ru", order_id=1, amount=100)
        paid_text = get_text("order_paid", "ru", order_id=1, amount=100)
        cancelled_text = get_text("order_cancelled", "ru", order_id=1)
        refunded_text = get_text("order_refunded", "ru", order_id=1, amount=100)

        # Each should have a status emoji
        assert "📝" in new_text  # New order
        assert "✅" in paid_text  # Paid order
        assert "❌" in cancelled_text  # Cancelled order
        assert "💸" in refunded_text  # Refund


class TestPaymentCallbackStatusUpdate:
    """Test that payment callback updates order status correctly."""

    @pytest.mark.asyncio
    async def test_success_callback_sets_paid_status(self):
        """Test successful callback sets PAID status."""
        from app.api.webhooks import payment_callback, PaymentCallbackRequest

        callback = PaymentCallbackRequest(
            order_id=123,
            status="success"
        )

        mock_order = MagicMock()
        mock_order.id = 123
        mock_order.user_id = 456
        mock_order.agent_id = 1
        mock_order.bill24_order_id = 789
        mock_order.total_amount = 5000
        mock_order.status = MagicMock()
        mock_order.paid_at = None

        mock_user = MagicMock()
        mock_user.telegram_chat_id = 111222333

        with patch('app.api.webhooks.OrderStatus') as mock_status:
            mock_status.PAID = "PAID"
            mock_status.REFUNDED = "REFUNDED"
            mock_status.CANCELLED = "CANCELLED"
            mock_order.status.__eq__ = lambda self, other: False

            mock_db = AsyncMock()

            call_count = [0]
            def get_result():
                call_count[0] += 1
                result = MagicMock()
                if call_count[0] == 1:
                    result.scalar_one_or_none.return_value = mock_order
                else:
                    result.scalar_one_or_none.return_value = mock_user
                return result

            mock_db.execute.side_effect = lambda *args, **kwargs: get_result()

            mock_background = MagicMock()

            with patch('app.api.webhooks.enqueue_ticket_delivery', new_callable=AsyncMock):
                with patch('app.api.webhooks.WebhookService') as mock_webhook_service:
                    mock_service_instance = MagicMock()
                    mock_service_instance.get_webhook_config = AsyncMock(return_value={
                        "is_active": False,
                        "events": []
                    })
                    mock_webhook_service.return_value = mock_service_instance

                    response = await payment_callback(callback, mock_background, mock_db)

                    # Order status should be set to PAID
                    assert mock_order.status == mock_status.PAID
                    assert response.status == "success"

    @pytest.mark.asyncio
    async def test_failure_callback_sets_cancelled_status(self):
        """Test failure callback sets CANCELLED status."""
        from app.api.webhooks import payment_callback, PaymentCallbackRequest

        callback = PaymentCallbackRequest(
            order_id=456,
            status="failure"
        )

        mock_order = MagicMock()
        mock_order.id = 456
        mock_order.status = MagicMock()

        with patch('app.api.webhooks.OrderStatus') as mock_status:
            mock_status.PAID = "PAID"
            mock_status.REFUNDED = "REFUNDED"
            mock_status.CANCELLED = "CANCELLED"
            mock_order.status.__eq__ = lambda self, other: False

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_order
            mock_db.execute.return_value = mock_result

            mock_background = MagicMock()

            response = await payment_callback(callback, mock_background, mock_db)

            # Order status should be set to CANCELLED
            assert mock_order.status == mock_status.CANCELLED
            assert "cancelled" in response.message.lower()


class TestOrderStatusModel:
    """Test OrderStatus enum."""

    def test_order_status_has_expected_values(self):
        """Test OrderStatus enum has expected values."""
        from app.models import OrderStatus

        # Should have these status values
        assert hasattr(OrderStatus, 'NEW')
        assert hasattr(OrderStatus, 'PENDING')
        assert hasattr(OrderStatus, 'PAID')
        assert hasattr(OrderStatus, 'CANCELLED')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
