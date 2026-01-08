"""
API Routes for TG-Ticket-Agent
"""

from fastapi import APIRouter

# Create routers
admin_router = APIRouter()
webhook_router = APIRouter()
widget_router = APIRouter()

# Import and include sub-routers
from . import admin, webhooks, widget  # noqa: F401, E402

__all__ = ["admin_router", "webhook_router", "widget_router"]
