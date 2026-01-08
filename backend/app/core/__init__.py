"""Core modules for TG-Ticket-Agent."""

from .config import settings
from .database import get_db, init_db

__all__ = ["settings", "get_db", "init_db"]
