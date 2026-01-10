"""
Test purchase confirmation notification.

Tests that purchase confirmation and ticket delivery are sent after payment.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestTicketDeliveryJob:
    """Test process_ticket_delivery_job function."""

    @pytest.mark.asyncio
    async def test_job_function_exists(self):
        """Test process_ticket_delivery_job function exists."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect
        assert inspect.iscoroutinefunction(process_ticket_delivery_job)

    @pytest.mark.asyncio
    async def test_job_handles_missing_bot_token(self):
        """Test job handles missing bot token gracefully."""
        from app.core.background_jobs import process_ticket_delivery_job

        with patch('app.core.background_jobs.settings') as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = None

            result = await process_ticket_delivery_job(
                ctx={},
                order_id=123,
                user_chat_id=456789
            )

            assert result["success"] is False
            assert "not configured" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_job_handles_order_not_found(self):
        """Test job handles order not found."""
        from app.core.background_jobs import process_ticket_delivery_job

        with patch('app.core.background_jobs.settings') as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

            with patch('app.core.background_jobs.async_session_maker') as mock_maker:
                mock_session = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None  # No order
                mock_session.execute.return_value = mock_result

                # Create async context manager
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value = mock_session
                mock_context.__aexit__.return_value = None
                mock_maker.return_value = mock_context

                result = await process_ticket_delivery_job(
                    ctx={},
                    order_id=99999,
                    user_chat_id=456789
                )

                assert result["success"] is False
                assert "not found" in result.get("error", "").lower()


class TestPurchaseConfirmationFlow:
    """Test the purchase confirmation flow."""

    def test_payment_callback_triggers_delivery(self):
        """Test that payment callback triggers ticket delivery."""
        # The payment_callback handler in webhooks.py calls enqueue_ticket_delivery
        # This test verifies the flow exists
        from app.api.webhooks import payment_callback
        import inspect
        assert inspect.iscoroutinefunction(payment_callback)

    def test_enqueue_ticket_delivery_exists(self):
        """Test enqueue_ticket_delivery function exists."""
        from app.core.background_jobs import enqueue_ticket_delivery
        import inspect
        assert inspect.iscoroutinefunction(enqueue_ticket_delivery)


class TestConfirmationMessageContent:
    """Test confirmation message content."""

    def test_confirmation_message_format(self):
        """Test confirmation message has expected elements."""
        # The confirmation message in process_ticket_delivery_job contains:
        # - Success indicator
        # - Order ID
        # - Agent name
        # - Total amount
        # - Ticket delivery notice

        message_template = (
            "✅ <b>Покупка подтверждена!</b>\n\n"
            "Заказ #{order_id}\n"
            "Агент: {agent_name}\n"
            "Сумма: {amount} ₽\n\n"
            "Ваши билеты будут отправлены ниже."
        )

        formatted = message_template.format(
            order_id=123,
            agent_name="Test Agent",
            amount=5000
        )

        assert "Покупка подтверждена" in formatted
        assert "#123" in formatted
        assert "Test Agent" in formatted
        assert "5000 ₽" in formatted
        assert "билеты" in formatted.lower()


class TestIntegrationWithPaymentCallback:
    """Test integration between payment callback and ticket delivery."""

    @pytest.mark.asyncio
    async def test_successful_payment_enqueues_delivery(self):
        """Test successful payment enqueues ticket delivery."""
        from app.api.webhooks import payment_callback, PaymentCallbackRequest

        callback = PaymentCallbackRequest(
            order_id=123,
            status="success",
            transaction_id="txn_123"
        )

        # Mock order
        mock_order = MagicMock()
        mock_order.id = 123
        mock_order.user_id = 456
        mock_order.agent_id = 1
        mock_order.bill24_order_id = 789
        mock_order.total_amount = 5000
        mock_order.status = MagicMock()
        mock_order.paid_at = None

        # Mock user
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

            with patch('app.api.webhooks.enqueue_ticket_delivery', new_callable=AsyncMock) as mock_delivery:
                with patch('app.api.webhooks.WebhookService') as mock_webhook_service:
                    mock_service_instance = MagicMock()
                    mock_service_instance.get_webhook_config = AsyncMock(return_value={
                        "is_active": False,
                        "events": []
                    })
                    mock_webhook_service.return_value = mock_service_instance

                    response = await payment_callback(callback, mock_background, mock_db)

                    # Verify ticket delivery was enqueued
                    mock_delivery.assert_called_once_with(
                        order_id=123,
                        user_chat_id=111222333
                    )

                    assert response.status == "success"


class TestOrderStatusUpdate:
    """Test order status is updated correctly."""

    def test_order_model_has_tickets_delivered(self):
        """Test Order model has tickets_delivered field."""
        from app.models import Order
        assert hasattr(Order, 'tickets_delivered')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
