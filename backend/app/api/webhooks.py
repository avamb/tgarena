"""
Webhook API Endpoints

Handles n8n integration and payment callbacks.
"""

from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel

from . import webhook_router


# =============================================================================
# Pydantic Models
# =============================================================================


class WebhookConfig(BaseModel):
    url: str
    events: list[str] = []
    is_active: bool = True


class WebhookLogResponse(BaseModel):
    id: int
    event_type: str
    payload: Dict[str, Any]
    response_status: Optional[int]
    success: bool
    sent_at: str


# =============================================================================
# Webhook Configuration (Admin)
# =============================================================================


@webhook_router.get("/config")
async def get_webhook_config():
    """Get current webhook configuration."""
    return {
        "url": "",
        "events": ["user.registered", "order.paid"],
        "is_active": False,
    }


@webhook_router.put("/config")
async def update_webhook_config(config: WebhookConfig):
    """Update webhook configuration."""
    # TODO: Implement
    return {"message": "Configuration updated", "config": config.model_dump()}


@webhook_router.get("/logs")
async def get_webhook_logs(page: int = 1, page_size: int = 20):
    """Get webhook call logs."""
    return {"logs": [], "total": 0}


@webhook_router.post("/test")
async def test_webhook(background_tasks: BackgroundTasks):
    """Send test webhook to configured URL."""
    # TODO: Implement
    return {"message": "Test webhook sent"}


# =============================================================================
# External Webhook Endpoints
# =============================================================================


@webhook_router.post("/n8n")
async def n8n_webhook(request: Request):
    """
    Webhook endpoint for n8n integration.

    Receives events from internal system and can trigger n8n workflows.
    """
    body = await request.json()
    # TODO: Validate and process webhook
    return {"status": "received", "event": body.get("event")}


@webhook_router.post("/payment-callback")
async def payment_callback(request: Request, background_tasks: BackgroundTasks):
    """
    Payment callback from acquiring system.

    Called after payment is processed to update order status
    and trigger ticket delivery.
    """
    body = await request.json()

    # TODO: Validate callback signature
    # TODO: Update order status
    # TODO: Trigger ticket delivery

    return {"status": "ok"}


@webhook_router.post("/telegram")
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint.

    Receives updates from Telegram when bot is in webhook mode.
    """
    body = await request.json()
    # TODO: Process Telegram update
    return {"status": "ok"}
