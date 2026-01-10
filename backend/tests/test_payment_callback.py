"""
Test payment callback processing.

Tests that payment callbacks update order status and trigger ticket delivery.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestPaymentCallbackModels:
    """Test payment callback Pydantic models."""

    def test_payment_callback_request_model(self):
        """Test PaymentCallbackRequest model."""
        from app.api.webhooks import PaymentCallbackRequest

        # Test with required fields only
        callback = PaymentCallbackRequest(
            order_id=123,
            status="success"
        )
        assert callback.order_id == 123
        assert callback.status == "success"
        assert callback.currency == "RUB"  # Default

    def test_payment_callback_request_with_all_fields(self):
        """Test PaymentCallbackRequest with all fields."""
        from app.api.webhooks import PaymentCallbackRequest

        callback = PaymentCallbackRequest(
            order_id=456,
            external_order_id="ext_12345",
            status="success",
            amount=5000.0,
            currency="USD",
            transaction_id="txn_abc123",
            signature="sig_xyz"
        )

        assert callback.order_id == 456
        assert callback.external_order_id == "ext_12345"
        assert callback.amount == 5000.0
        assert callback.currency == "USD"
        assert callback.transaction_id == "txn_abc123"
        assert callback.signature == "sig_xyz"

    def test_payment_callback_response_model(self):
        """Test PaymentCallbackResponse model."""
        from app.api.webhooks import PaymentCallbackResponse

        response = PaymentCallbackResponse(
            status="success",
            order_id=123,
            message="Order processed"
        )

        assert response.status == "success"
        assert response.order_id == 123
        assert response.message == "Order processed"


class TestPaymentCallbackHandler:
    """Test payment callback handler functionality."""

    @pytest.mark.asyncio
    async def test_callback_order_not_found(self):
        """Test callback returns 404 when order not found."""
        from app.api.webhooks import payment_callback, PaymentCallbackRequest
        from fastapi import HTTPException

        callback = PaymentCallbackRequest(order_id=99999, status="success")

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        mock_background = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await payment_callback(callback, mock_background, mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_callback_success_updates_order(self):
        """Test successful payment updates order status."""
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
        mock_order.status.value = "PENDING"

        # Mock status enum
        with patch('app.api.webhooks.OrderStatus') as mock_status:
            mock_status.PAID = "PAID"
            mock_status.REFUNDED = "REFUNDED"
            mock_status.CANCELLED = "CANCELLED"

            # Need to configure status comparison
            mock_order.status = MagicMock()
            mock_order.status.__eq__ = lambda self, other: False

            # Mock user
            mock_user = MagicMock()
            mock_user.telegram_chat_id = 111222333

            mock_db = AsyncMock()

            # Setup execute to return order first, then user
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

            # Mock ticket delivery and webhook
            with patch('app.api.webhooks.enqueue_ticket_delivery', new_callable=AsyncMock) as mock_delivery:
                with patch('app.api.webhooks.WebhookService') as mock_webhook_service:
                    mock_service_instance = MagicMock()
                    mock_service_instance.get_webhook_config = AsyncMock(return_value={
                        "is_active": False,
                        "events": []
                    })
                    mock_webhook_service.return_value = mock_service_instance

                    response = await payment_callback(callback, mock_background, mock_db)

                    assert response.status == "success"
                    assert response.order_id == 123
                    assert "paid" in response.message.lower()

                    # Verify ticket delivery was triggered
                    mock_delivery.assert_called_once_with(
                        order_id=123,
                        user_chat_id=111222333
                    )

    @pytest.mark.asyncio
    async def test_callback_failure_cancels_order(self):
        """Test failed payment cancels order."""
        from app.api.webhooks import payment_callback, PaymentCallbackRequest

        callback = PaymentCallbackRequest(
            order_id=123,
            status="failure"
        )

        # Mock order
        mock_order = MagicMock()
        mock_order.id = 123
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

            assert response.status == "processed"
            assert response.order_id == 123
            assert "cancelled" in response.message.lower()

    @pytest.mark.asyncio
    async def test_callback_ignores_already_paid(self):
        """Test callback ignores already paid orders."""
        from app.api.webhooks import payment_callback, PaymentCallbackRequest

        callback = PaymentCallbackRequest(
            order_id=123,
            status="success"
        )

        # Mock order that's already paid
        mock_order = MagicMock()
        mock_order.id = 123

        with patch('app.api.webhooks.OrderStatus') as mock_status:
            mock_status.PAID = "PAID"
            mock_status.REFUNDED = "REFUNDED"
            mock_order.status = mock_status.PAID
            mock_order.status.value = "PAID"

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_order
            mock_db.execute.return_value = mock_result

            mock_background = MagicMock()

            response = await payment_callback(callback, mock_background, mock_db)

            assert response.status == "ignored"
            assert "already" in response.message.lower()


class TestPaymentCallbackWorkflow:
    """Test complete payment callback workflow."""

    def test_workflow_steps_documented(self):
        """Test that all workflow steps are implemented."""
        from app.api import webhooks

        # Verify payment_callback handler exists
        assert hasattr(webhooks, 'payment_callback')

        # Verify it's an async function
        import inspect
        assert inspect.iscoroutinefunction(webhooks.payment_callback)

    def test_ticket_delivery_enqueue_exists(self):
        """Test enqueue_ticket_delivery function exists."""
        from app.core.background_jobs import enqueue_ticket_delivery
        import inspect
        assert inspect.iscoroutinefunction(enqueue_ticket_delivery)

    def test_webhook_service_send_webhook_exists(self):
        """Test WebhookService.send_webhook method exists."""
        from app.core.webhook_service import WebhookService
        assert hasattr(WebhookService, 'send_webhook')


class TestTicketDeliveryTrigger:
    """Test that ticket delivery is properly triggered."""

    @pytest.mark.asyncio
    async def test_ticket_delivery_job_function(self):
        """Test process_ticket_delivery_job function exists."""
        from app.core.background_jobs import process_ticket_delivery_job
        import inspect
        assert inspect.iscoroutinefunction(process_ticket_delivery_job)

    @pytest.mark.asyncio
    async def test_enqueue_ticket_delivery(self):
        """Test enqueue_ticket_delivery queues job."""
        from app.core.background_jobs import enqueue_ticket_delivery

        with patch('app.core.background_jobs.get_arq_pool') as mock_get_pool:
            mock_pool = AsyncMock()
            mock_job = MagicMock()
            mock_job.job_id = "test_job_123"
            mock_pool.enqueue_job.return_value = mock_job
            mock_get_pool.return_value = mock_pool

            job = await enqueue_ticket_delivery(order_id=123, user_chat_id=456)

            mock_pool.enqueue_job.assert_called_once_with(
                "process_ticket_delivery_job", 123, 456
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
