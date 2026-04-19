"""
Application Configuration

Loads settings from environment variables with sensible defaults.
"""

from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    PORT: int = 3001
    ENV: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/tg_ticket_agent"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_BOT_USERNAME: Optional[str] = None

    # Bill24 API
    BILL24_TEST_URL: str = "https://api.tixgear.com:1240/json"
    BILL24_REAL_URL: str = "https://api.tixgear.com/json"
    BILL24_DEFAULT_ZONE: str = "test"

    # Admin Authentication
    ADMIN_JWT_SECRET: str = "change-me-in-production"
    ADMIN_JWT_EXPIRES_IN: str = "24h"
    ADMIN_DEFAULT_USERNAME: str = "admin"
    ADMIN_DEFAULT_PASSWORD: str = "changeme123"

    # Webhooks
    N8N_WEBHOOK_URL: Optional[str] = None
    WEBHOOK_SECRET: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Feature Flags
    ENABLE_TICKET_PDF: bool = True
    ENABLE_WEBHOOKS: bool = True
    ENABLE_EVENT_CACHING: bool = True
    EVENT_CACHE_TTL: int = 900  # 15 minutes

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
