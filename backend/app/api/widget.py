"""
Widget API Endpoints

Handles Telegram WebApp authentication and session management for the widget.
"""

from typing import Optional

from fastapi import HTTPException, status
from pydantic import BaseModel

from . import widget_router


# =============================================================================
# Pydantic Models
# =============================================================================


class WidgetAuthRequest(BaseModel):
    """Request model for widget authentication."""

    init_data: str  # Telegram WebApp initData
    agent_id: int


class WidgetAuthResponse(BaseModel):
    """Response model for widget authentication."""

    user_id: int  # Bill24 userId
    session_id: str  # Bill24 sessionId
    chat_id: int  # Telegram chat_id
    agent_fid: int  # Agent's Bill24 FID
    zone: str  # 'test' or 'real'


class UserSessionResponse(BaseModel):
    """Response model for user session lookup."""

    user_id: int
    session_id: str
    agent_fid: int
    zone: str
    bill24_api_url: str


# =============================================================================
# Widget Authentication Endpoints
# =============================================================================


@widget_router.post("/auth", response_model=WidgetAuthResponse)
async def widget_auth(request: WidgetAuthRequest):
    """
    Authenticate widget user via Telegram initData.

    1. Validates Telegram initData signature
    2. Extracts user info from initData
    3. Looks up or creates Bill24 session
    4. Returns session credentials for widget
    """
    # TODO: Implement Telegram initData validation
    # TODO: Look up user by chat_id
    # TODO: Get or create Bill24 session

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Widget authentication not yet implemented",
    )


@widget_router.get("/user/{chat_id}", response_model=UserSessionResponse)
async def get_user_session(chat_id: int, agent_id: Optional[int] = None):
    """
    Get Bill24 session for user by Telegram chat_id.

    Used by widget to retrieve existing session without re-authentication.
    """
    # TODO: Look up active session for user

    raise HTTPException(status_code=404, detail="Session not found")


@widget_router.post("/user/{chat_id}/refresh-session")
async def refresh_user_session(chat_id: int):
    """
    Refresh Bill24 session for user.

    Creates new session if current one is expired or invalid.
    """
    # TODO: Implement session refresh

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Session refresh not yet implemented",
    )
