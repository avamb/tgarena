"""
TG-Ticket-Agent FastAPI Application Entry Point
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    # When running from backend directory (e.g., uvicorn app.main:app)
    from app.api import admin_router, webhook_router, widget_router
    from app.core.config import settings
    from app.core.database import init_db
    from app.core.redis_client import get_redis_client, close_redis_client, ping_redis
    # Import models to register them with Base.metadata
    from app import models  # noqa: F401
except ModuleNotFoundError:
    # When running from root with backend prefix (e.g., docker-compose)
    from backend.app.api import admin_router, webhook_router, widget_router
    from backend.app.core.config import settings
    from backend.app.core.database import init_db
    from backend.app.core.redis_client import get_redis_client, close_redis_client, ping_redis
    # Import models to register them with Base.metadata
    from backend.app import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Configure structured logging
    try:
        from app.core.logging_config import setup_logging
    except ModuleNotFoundError:
        from backend.app.core.logging_config import setup_logging

    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )

    # Startup
    await init_db()
    # Initialize Redis connection
    await get_redis_client()
    yield
    # Shutdown
    await close_redis_client()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="TG-Ticket-Agent API",
        description="API for TG-Ticket-Agent - Multi-agent Telegram ticket bot",
        version="0.1.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
    app.include_router(webhook_router, prefix="/api/webhooks", tags=["Webhooks"])
    app.include_router(widget_router, prefix="/api/widget", tags=["Widget"])

    return app


app = create_application()


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Dokploy and monitoring."""
    redis_connected = await ping_redis()
    return {
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.ENV,
        "redis": "connected" if redis_connected else "disconnected",
    }
