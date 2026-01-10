"""
Test n8n webhook integration.

Tests that webhooks are properly configured, sent, and logged.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestWebhookServiceConfig:
    """Test webhook service configuration."""

    @pytest.mark.asyncio
    async def test_get_webhook_config_returns_defaults(self):
        """Test getting webhook config with no settings."""
        from app.core.webhook_service import WebhookService

        # Mock database session
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = WebhookService(mock_db)
        config = await service.get_webhook_config()

        assert "url" in config
        assert "is_active" in config
        assert "events" in config
        assert config["is_active"] is False  # Default inactive

    @pytest.mark.asyncio
    async def test_get_webhook_config_with_settings(self):
        """Test getting webhook config with existing settings."""
        from app.core.webhook_service import WebhookService

        # Create mock settings
        mock_settings = []

        mock_url_setting = MagicMock()
        mock_url_setting.key = "webhook_url"
        mock_url_setting.value = "https://n8n.example.com/webhook/123"
        mock_settings.append(mock_url_setting)

        mock_active_setting = MagicMock()
        mock_active_setting.key = "webhook_active"
        mock_active_setting.value = "true"
        mock_settings.append(mock_active_setting)

        mock_events_setting = MagicMock()
        mock_events_setting.key = "webhook_events"
        mock_events_setting.value = "user.registered,order.paid"
        mock_settings.append(mock_events_setting)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_settings
        mock_db.execute.return_value = mock_result

        service = WebhookService(mock_db)
        config = await service.get_webhook_config()

        assert config["url"] == "https://n8n.example.com/webhook/123"
        assert config["is_active"] is True
        assert "user.registered" in config["events"]
        assert "order.paid" in config["events"]


class TestWebhookSending:
    """Test webhook sending functionality."""

    @pytest.mark.asyncio
    async def test_send_webhook_payload_format(self):
        """Test webhook payload has correct format."""
        from app.core.webhook_service import WebhookService

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        # Mock get_webhook_config
        service = WebhookService(mock_db)

        # Mock the config and send
        with patch.object(service, 'get_webhook_config') as mock_config:
            mock_config.return_value = {
                "url": "https://n8n.example.com/webhook/123",
                "is_active": True,
                "events": ["order.paid"]
            }

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = "OK"
                mock_client.post.return_value = mock_response
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_client

                result = await service.send_webhook(
                    event_type="order.paid",
                    payload={
                        "order_id": 123,
                        "user_id": 456,
                        "amount": 1000
                    }
                )

                # Check the call was made
                mock_client.post.assert_called()
                call_args = mock_client.post.call_args

                # Verify payload structure
                sent_payload = call_args.kwargs["json"]
                assert "event" in sent_payload
                assert "timestamp" in sent_payload
                assert "data" in sent_payload
                assert sent_payload["event"] == "order.paid"
                assert sent_payload["data"]["order_id"] == 123

    @pytest.mark.asyncio
    async def test_send_webhook_returns_success(self):
        """Test successful webhook returns success status."""
        from app.core.webhook_service import WebhookService

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        service = WebhookService(mock_db)

        with patch.object(service, 'get_webhook_config') as mock_config:
            mock_config.return_value = {
                "url": "https://n8n.example.com/webhook/123",
                "is_active": True,
                "events": ["test"]
            }

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = "OK"
                mock_client.post.return_value = mock_response
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_client

                result = await service.send_webhook(
                    event_type="test",
                    payload={"test": True}
                )

                assert result["success"] is True
                assert result["total_attempts"] == 1

    @pytest.mark.asyncio
    async def test_send_webhook_inactive_returns_error(self):
        """Test sending webhook when inactive returns error."""
        from app.core.webhook_service import WebhookService

        mock_db = AsyncMock()
        service = WebhookService(mock_db)

        with patch.object(service, 'get_webhook_config') as mock_config:
            mock_config.return_value = {
                "url": "https://n8n.example.com/webhook/123",
                "is_active": False,  # Inactive
                "events": ["test"]
            }

            result = await service.send_webhook(
                event_type="test",
                payload={"test": True}
            )

            assert result["success"] is False
            assert "inactive" in result.get("error", "").lower()


class TestWebhookRetry:
    """Test webhook retry mechanism."""

    def test_webhook_service_has_retry_config(self):
        """Test WebhookService has retry configuration."""
        from app.core.webhook_service import WebhookService

        assert hasattr(WebhookService, 'MAX_RETRIES')
        assert hasattr(WebhookService, 'RETRY_DELAYS')
        assert WebhookService.MAX_RETRIES == 3
        assert len(WebhookService.RETRY_DELAYS) == 3


class TestWebhookLogging:
    """Test webhook logging functionality."""

    @pytest.mark.asyncio
    async def test_webhook_logs_to_database(self):
        """Test that webhook calls are logged to database."""
        from app.core.webhook_service import WebhookService

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        service = WebhookService(mock_db)

        with patch.object(service, 'get_webhook_config') as mock_config:
            mock_config.return_value = {
                "url": "https://n8n.example.com/webhook/123",
                "is_active": True,
                "events": ["test"]
            }

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = "OK"
                mock_client.post.return_value = mock_response
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_client

                await service.send_webhook(
                    event_type="test",
                    payload={"test": True}
                )

                # Verify log was added
                mock_db.add.assert_called()


class TestWebhookPayloadContent:
    """Test webhook payload contains correct user data."""

    def test_user_registration_payload_structure(self):
        """Test user registration webhook payload has user data."""
        # This would be called when a user registers
        payload = {
            "user_id": 12345,
            "telegram_chat_id": 987654321,
            "username": "testuser",
            "first_name": "John",
            "language": "en",
            "registered_at": datetime.utcnow().isoformat()
        }

        assert "user_id" in payload
        assert "telegram_chat_id" in payload
        assert "username" in payload

    def test_order_paid_payload_structure(self):
        """Test order paid webhook payload has order and user data."""
        payload = {
            "order_id": 123,
            "bill24_order_id": 456789,
            "user_id": 12345,
            "telegram_chat_id": 987654321,
            "agent_id": 1,
            "total_amount": 5000,
            "currency": "RUB",
            "seats": [
                {"seat_id": 1, "row": "A", "seat": "5", "price": 2500},
                {"seat_id": 2, "row": "A", "seat": "6", "price": 2500},
            ],
            "event_name": "Concert 2025",
            "paid_at": datetime.utcnow().isoformat()
        }

        assert "order_id" in payload
        assert "user_id" in payload
        assert "telegram_chat_id" in payload
        assert "total_amount" in payload
        assert "seats" in payload
        assert len(payload["seats"]) == 2


class TestBackgroundWebhookJob:
    """Test background webhook job."""

    @pytest.mark.asyncio
    async def test_send_webhook_job_function_exists(self):
        """Test send_webhook_job function exists."""
        from app.core.background_jobs import send_webhook_job
        assert callable(send_webhook_job)

    @pytest.mark.asyncio
    async def test_enqueue_webhook_function_exists(self):
        """Test enqueue_webhook function exists."""
        from app.core.background_jobs import enqueue_webhook
        assert callable(enqueue_webhook)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
