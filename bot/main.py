"""
TG-Ticket-Agent Bot Entry Point

Delegates to the backend bot runner which has full Bill24 integration,
database access, and proper handler implementations.

This file exists for backward compatibility. The real implementation
lives in backend/app/bot/runner.py with handlers in backend/app/bot/handlers.py.
"""

import sys
from pathlib import Path

# Ensure project root is on the path so backend imports work
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.bot.runner import main

if __name__ == "__main__":
    main()
