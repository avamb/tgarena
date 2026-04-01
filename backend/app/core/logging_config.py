"""
Structured Logging Configuration

Provides JSON-formatted logging with file rotation and an in-memory
ring buffer for serving logs via the admin API endpoint.
"""

import json
import logging
import logging.handlers
import os
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# Maximum number of log entries kept in memory for API access
MAX_LOG_ENTRIES = 5000

# Thread-safe ring buffer for log entries
_log_buffer: deque = deque(maxlen=MAX_LOG_ENTRIES)
_log_lock = threading.Lock()


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Determine component from logger name
        if record.name.startswith("app.bot") or record.name.startswith("backend.app.bot"):
            log_entry["component"] = "bot"
        elif record.name.startswith("app.api") or record.name.startswith("backend.app.api"):
            log_entry["component"] = "api"
        elif record.name.startswith("app.services.bill24") or record.name.startswith("backend.app.services.bill24"):
            log_entry["component"] = "bill24"
        elif record.name.startswith("uvicorn") or record.name.startswith("fastapi"):
            log_entry["component"] = "api"
        else:
            log_entry["component"] = "system"

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class BufferHandler(logging.Handler):
    """
    Logging handler that stores entries in an in-memory ring buffer.
    Used by the admin API to serve recent logs without reading files.
    """

    def emit(self, record: logging.LogRecord):
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            # Determine component
            if record.name.startswith(("app.bot", "backend.app.bot")):
                entry["component"] = "bot"
            elif record.name.startswith(("app.api", "backend.app.api")):
                entry["component"] = "api"
            elif record.name.startswith(("app.services.bill24", "backend.app.services.bill24")):
                entry["component"] = "bill24"
            elif record.name.startswith(("uvicorn", "fastapi")):
                entry["component"] = "api"
            else:
                entry["component"] = "system"

            # Add exception info
            if record.exc_info and record.exc_info[0] is not None:
                formatter = logging.Formatter()
                entry["exception"] = formatter.formatException(record.exc_info)

            with _log_lock:
                _log_buffer.append(entry)

        except Exception:
            self.handleError(record)


def get_log_entries(
    lines: int = 100,
    level: Optional[str] = None,
    component: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get log entries from the in-memory buffer with optional filtering.

    Args:
        lines: Maximum number of entries to return
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        component: Filter by component (bot, api, bill24, system)
        search: Search string to match in log messages

    Returns:
        List of log entry dicts, most recent first
    """
    with _log_lock:
        entries = list(_log_buffer)

    # Filter by level
    if level:
        level_upper = level.upper()
        level_num = getattr(logging, level_upper, None)
        if level_num is not None:
            # Include entries at or above the specified level
            entries = [
                e for e in entries
                if getattr(logging, e.get("level", "DEBUG"), 0) >= level_num
            ]

    # Filter by component
    if component:
        entries = [e for e in entries if e.get("component") == component.lower()]

    # Filter by search term
    if search:
        search_lower = search.lower()
        entries = [
            e for e in entries
            if search_lower in e.get("message", "").lower()
            or search_lower in e.get("logger", "").lower()
            or search_lower in str(e.get("exception", "")).lower()
        ]

    # Return most recent entries first, limited to requested count
    entries.reverse()
    return entries[:lines]


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_dir: Optional[str] = None,
):
    """
    Configure application-wide structured logging.

    Sets up:
    - Console handler with JSON or text format
    - File handler with rotation (10MB, 5 backups)
    - In-memory buffer handler for API access

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        log_format: Output format ('json' or 'text')
        log_dir: Directory for log files (default: logs/)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # JSON formatter for structured output
    json_formatter = JSONFormatter()

    # Text formatter for human-readable output
    text_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Choose formatter based on config
    formatter = json_formatter if log_format == "json" else text_formatter

    # Console handler (always active)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    if log_dir is None:
        log_dir = os.path.join(os.getcwd(), "logs")

    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(json_formatter)  # Always JSON in files
        root_logger.addHandler(file_handler)
    except Exception as e:
        # If file logging fails, continue with console only
        root_logger.warning(f"Could not set up file logging: {e}")

    # In-memory buffer handler for API access
    buffer_handler = BufferHandler()
    buffer_handler.setLevel(logging.DEBUG)  # Capture all levels in buffer
    root_logger.addHandler(buffer_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    root_logger.info("Structured logging configured", extra={
        "log_level": log_level,
        "log_format": log_format,
        "log_dir": log_dir,
    })
