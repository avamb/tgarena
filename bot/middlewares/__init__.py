"""
Bot Middlewares

Middlewares for rate limiting, user tracking, and localization.
"""

from aiogram import Dispatcher
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Update


class ThrottlingMiddleware(BaseMiddleware):
    """Simple rate limiting middleware."""

    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self._last_request: dict = {}

    async def __call__(self, handler, event: Update, data: dict):
        # TODO: Implement actual rate limiting with Redis
        return await handler(event, data)


class UserTrackingMiddleware(BaseMiddleware):
    """Middleware to track user activity."""

    async def __call__(self, handler, event: Update, data: dict):
        # TODO: Update user's last_active_at
        return await handler(event, data)


class LocalizationMiddleware(BaseMiddleware):
    """Middleware for message localization."""

    async def __call__(self, handler, event: Update, data: dict):
        # TODO: Load user's preferred language
        data["locale"] = "ru"  # Default to Russian
        return await handler(event, data)


def register_middlewares(dp: Dispatcher):
    """Register all middlewares with dispatcher."""
    dp.update.middleware(ThrottlingMiddleware())
    dp.update.middleware(UserTrackingMiddleware())
    dp.update.middleware(LocalizationMiddleware())
