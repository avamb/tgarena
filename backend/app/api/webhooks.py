"""
Webhook API Endpoints

Handles n8n integration and payment callbacks.
Includes retry logic for webhook delivery.
"""

from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from . import webhook_router

try:
    from app.core import get_current_admin_user, AdminUser, get_db
    from app.core.webhook_service import WebhookService
except ModuleNotFoundError:
    from backend.app.core import get_current_admin_user, AdminUser, get_db
    from backend.app.core.webhook_service import WebhookService


# =============================================================================
# Pydantic Models
# =============================================================================


class WebhookConfig(BaseModel):
    url: str
    events: List[str] = []
    is_active: bool = True


class WebhookConfigResponse(BaseModel):
    url: str
    events: List[str]
    is_active: bool


class WebhookLogResponse(BaseModel):
    id: int
    event_type: str
    payload: Dict[str, Any]
    response_status: Optional[int]
    response_body: Optional[str]
    success: bool
    sent_at: str


class WebhookLogsResponse(BaseModel):
    logs: List[WebhookLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class WebhookTestRequest(BaseModel):
    url: Optional[str] = None  # Optional override URL for testing


class WebhookTestResponse(BaseModel):
    success: bool
    attempts: List[Dict[str, Any]]
    total_attempts: int
    error: Optional[str] = None
    log_id: Optional[int] = None


# =============================================================================
# Webhook Configuration (Admin - Protected)
# =============================================================================


@webhook_router.get("/config", response_model=WebhookConfigResponse)
async def get_webhook_config(
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current webhook configuration. Requires authentication."""
    service = WebhookService(db)
    config = await service.get_webhook_config()
    return WebhookConfigResponse(
        url=config["url"],
        events=config["events"],
        is_active=config["is_active"],
    )


@webhook_router.put("/config", response_model=WebhookConfigResponse)
async def update_webhook_config(
    config: WebhookConfig,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update webhook configuration. Requires authentication."""
    service = WebhookService(db)
    await service.save_webhook_config(
        url=config.url,
        events=config.events,
        is_active=config.is_active,
    )
    return WebhookConfigResponse(
        url=config.url,
        events=config.events,
        is_active=config.is_active,
    )


@webhook_router.get("/logs", response_model=WebhookLogsResponse)
async def get_webhook_logs(
    page: int = 1,
    page_size: int = 20,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get webhook call logs with pagination. Requires authentication."""
    service = WebhookService(db)
    result = await service.get_logs(page=page, page_size=page_size)
    return WebhookLogsResponse(**result)


@webhook_router.post("/test", response_model=WebhookTestResponse)
async def test_webhook(
    request: Optional[WebhookTestRequest] = None,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send test webhook to configured URL (or override URL).
    Includes retry logic - will attempt up to 3 times with exponential backoff.
    Requires authentication.
    """
    service = WebhookService(db)
    url = request.url if request else None
    result = await service.test_webhook(url=url)
    return WebhookTestResponse(**result)


# =============================================================================
# External Webhook Endpoints (No auth - called by external services)
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
