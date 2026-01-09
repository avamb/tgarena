"""
Webhook Service

Handles sending webhooks with retry logic and logging.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for sending webhooks with retry logic."""

    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 5, 15]  # seconds between retries (exponential backoff)
    TIMEOUT = 10  # seconds

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_webhook_config(self) -> Dict[str, Any]:
        """Get webhook configuration from system_settings."""
        try:
            from app.models import SystemSetting
        except ModuleNotFoundError:
            from backend.app.models import SystemSetting

        from sqlalchemy import select

        result = await self.db.execute(
            select(SystemSetting).where(SystemSetting.key.like("webhook_%"))
        )
        settings = result.scalars().all()

        config = {
            "url": "",
            "is_active": False,
            "events": ["user.registered", "order.paid"],
        }

        for setting in settings:
            if setting.key == "webhook_url":
                config["url"] = setting.value
            elif setting.key == "webhook_active":
                config["is_active"] = setting.value.lower() == "true"
            elif setting.key == "webhook_events":
                config["events"] = setting.value.split(",") if setting.value else []

        return config

    async def save_webhook_config(
        self, url: str, events: list[str], is_active: bool
    ) -> None:
        """Save webhook configuration to system_settings."""
        try:
            from app.models import SystemSetting
        except ModuleNotFoundError:
            from backend.app.models import SystemSetting

        from sqlalchemy import select

        # Update or create each setting
        settings_to_save = [
            ("webhook_url", url, "n8n webhook endpoint URL"),
            ("webhook_active", str(is_active).lower(), "Whether webhooks are active"),
            ("webhook_events", ",".join(events), "Comma-separated list of events"),
        ]

        for key, value, description in settings_to_save:
            result = await self.db.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            setting = result.scalar_one_or_none()

            if setting:
                setting.value = value
                setting.description = description
            else:
                new_setting = SystemSetting(
                    key=key, value=value, description=description
                )
                self.db.add(new_setting)

        await self.db.flush()

    async def send_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any],
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a webhook with retry logic.

        Args:
            event_type: Type of event (e.g., "user.registered", "order.paid")
            payload: Data to send
            url: Optional override URL (uses config URL if not provided)

        Returns:
            Dict with success status, attempts, and final response
        """
        try:
            from app.models import WebhookLog
        except ModuleNotFoundError:
            from backend.app.models import WebhookLog

        # Get URL from config if not provided
        if not url:
            config = await self.get_webhook_config()
            url = config.get("url")
            if not url or not config.get("is_active"):
                return {
                    "success": False,
                    "error": "Webhook not configured or inactive",
                    "attempts": 0,
                }

        # Prepare webhook payload
        webhook_payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload,
        }

        # Track attempts
        attempts = []
        last_error = None
        success = False
        response_status = None
        response_body = None

        # Try sending with retries
        for attempt in range(self.MAX_RETRIES):
            attempt_info = {
                "attempt": attempt + 1,
                "timestamp": datetime.utcnow().isoformat(),
            }

            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                    response = await client.post(
                        url,
                        json=webhook_payload,
                        headers={"Content-Type": "application/json"},
                    )

                    response_status = response.status_code
                    response_body = response.text[:1000]  # Limit response body size

                    attempt_info["status"] = response_status
                    attempt_info["success"] = 200 <= response_status < 300

                    if attempt_info["success"]:
                        success = True
                        attempts.append(attempt_info)
                        break
                    else:
                        attempt_info["error"] = f"HTTP {response_status}"
                        last_error = f"HTTP {response_status}: {response_body[:200]}"

            except httpx.TimeoutException:
                attempt_info["error"] = "Timeout"
                attempt_info["success"] = False
                last_error = "Connection timeout"
                logger.warning(f"Webhook timeout on attempt {attempt + 1}")

            except httpx.RequestError as e:
                attempt_info["error"] = str(e)
                attempt_info["success"] = False
                last_error = str(e)
                logger.warning(f"Webhook request error on attempt {attempt + 1}: {e}")

            except Exception as e:
                attempt_info["error"] = str(e)
                attempt_info["success"] = False
                last_error = str(e)
                logger.error(f"Webhook unexpected error on attempt {attempt + 1}: {e}")

            attempts.append(attempt_info)

            # Wait before retry (if not last attempt)
            if attempt < self.MAX_RETRIES - 1:
                delay = self.RETRY_DELAYS[attempt]
                logger.info(f"Webhook retry in {delay} seconds...")
                await asyncio.sleep(delay)

        # Log the webhook call to database
        log_entry = WebhookLog(
            event_type=event_type,
            payload=webhook_payload,
            response_status=response_status,
            response_body=response_body,
            success=success,
            sent_at=datetime.utcnow(),
        )
        self.db.add(log_entry)
        await self.db.flush()

        result = {
            "success": success,
            "attempts": attempts,
            "total_attempts": len(attempts),
            "log_id": log_entry.id,
        }

        if not success:
            result["error"] = last_error
            logger.error(
                f"Webhook failed after {len(attempts)} attempts: {last_error}"
            )
        else:
            logger.info(
                f"Webhook sent successfully on attempt {len(attempts)}"
            )

        return result

    async def test_webhook(self, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a test webhook to verify configuration.

        Args:
            url: Optional URL override for testing

        Returns:
            Result of webhook send operation
        """
        test_payload = {
            "message": "This is a test webhook from TG-Ticket-Agent",
            "test": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self.send_webhook(
            event_type="test",
            payload=test_payload,
            url=url,
        )

    async def get_logs(
        self, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Get webhook logs with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Dict with logs and total count
        """
        try:
            from app.models import WebhookLog
        except ModuleNotFoundError:
            from backend.app.models import WebhookLog

        from sqlalchemy import select, func

        # Get total count
        count_result = await self.db.execute(select(func.count(WebhookLog.id)))
        total = count_result.scalar() or 0

        # Get paginated logs
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(WebhookLog)
            .order_by(WebhookLog.sent_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        logs = result.scalars().all()

        return {
            "logs": [
                {
                    "id": log.id,
                    "event_type": log.event_type,
                    "payload": log.payload,
                    "response_status": log.response_status,
                    "response_body": log.response_body,
                    "success": log.success,
                    "sent_at": log.sent_at.isoformat(),
                }
                for log in logs
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }


# Helper function to create webhook service instance
async def get_webhook_service(db: AsyncSession) -> WebhookService:
    """Factory function to create WebhookService instance."""
    return WebhookService(db)
