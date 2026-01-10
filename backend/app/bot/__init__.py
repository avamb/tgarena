"""
TG-Ticket-Agent Telegram Bot Module

This module contains the Telegram bot implementation using aiogram 3.x.
"""

from .bot import create_bot, dp
from .handlers import register_handlers

__all__ = ["create_bot", "dp", "register_handlers"]
