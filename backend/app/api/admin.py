"""
Admin Panel API Endpoints

Handles authentication, agents, users, orders, dashboard, and webhooks management.
All protected routes require JWT authentication via Bearer token.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from . import admin_router

try:
    from app.core import (
        settings,
        get_current_admin_user,
        get_password_hash,
        verify_password,
        create_access_token,
        AdminUser,
    )
except ModuleNotFoundError:
    from backend.app.core import (
        settings,
        get_current_admin_user,
        get_password_hash,
        verify_password,
        create_access_token,
        AdminUser,
    )


# =============================================================================
# Pydantic Models (Schemas)
# =============================================================================


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AgentCreate(BaseModel):
    name: str
    fid: int
    token: str
    zone: str = "test"
    is_active: bool = True


class AgentResponse(BaseModel):
    """Response schema for Agent.

    Note: Agent identification uses internal agent.id (NOT fid or token).
    Deep link format: ?start=agent_{agent_id}
    The fid is the Bill24 frontend ID used for API calls, but NOT for deep links.
    """
    id: int
    name: str
    fid: int  # Bill24 frontend ID (for API calls, NOT for deep links)
    zone: str
    is_active: bool
    created_at: datetime
    deep_link: str  # Generated using agent.id, NOT fid

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    telegram_chat_id: int
    telegram_username: Optional[str]
    telegram_first_name: str
    telegram_last_name: Optional[str]
    preferred_language: str
    current_agent_id: Optional[int]
    created_at: datetime
    last_active_at: Optional[datetime]

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    user_id: int
    agent_id: int
    bil24_order_id: int
    status: str
    total_sum: float
    ticket_count: int
    created_at: datetime
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_users: int
    total_orders: int
    total_revenue: float
    active_agents: int
    orders_today: int
    revenue_today: float


# =============================================================================
# Authentication Endpoints (No auth required)
# =============================================================================


@admin_router.post("/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    """Authenticate admin user and return JWT token.

    For development, uses default credentials from settings.
    In production, this should authenticate against the database.
    """
    # Check against default admin credentials (for development)
    # In production, this should check against the database
    if (request.username == settings.ADMIN_DEFAULT_USERNAME and
        request.password == settings.ADMIN_DEFAULT_PASSWORD):
        # Create JWT token
        access_token = create_access_token(
            data={
                "sub": request.username,
                "user_id": 1,
                "role": "super_admin"
            }
        )
        return LoginResponse(access_token=access_token)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


@admin_router.post("/refresh")
async def refresh_token(current_user: AdminUser = Depends(get_current_admin_user)):
    """Refresh JWT token."""
    # Create new token with same user data
    access_token = create_access_token(
        data={
            "sub": current_user.username,
            "user_id": current_user.id,
            "role": current_user.role
        }
    )
    return LoginResponse(access_token=access_token)


@admin_router.post("/logout")
async def admin_logout():
    """Logout admin user.

    Note: JWT tokens are stateless, so logout is handled client-side
    by removing the token. This endpoint exists for API completeness.
    """
    return {"message": "Logged out successfully"}


# =============================================================================
# Agent Management Endpoints (Auth required)
# =============================================================================


@admin_router.get("/agents", response_model=List[AgentResponse])
async def list_agents(current_user: AdminUser = Depends(get_current_admin_user)):
    """Get all agents. Requires authentication."""
    # TODO: Implement database query
    return []


@admin_router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get agent by ID. Requires authentication."""
    raise HTTPException(status_code=404, detail="Agent not found")


@admin_router.post("/agents", response_model=AgentResponse)
async def create_agent(
    agent: AgentCreate,
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Create new agent. Requires authentication."""
    # TODO: Implement
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Agent creation not yet implemented",
    )


@admin_router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent: AgentCreate,
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Update existing agent. Requires authentication."""
    raise HTTPException(status_code=404, detail="Agent not found")


@admin_router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Delete agent. Requires authentication."""
    raise HTTPException(status_code=404, detail="Agent not found")


@admin_router.get("/agents/{agent_id}/stats")
async def get_agent_stats(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get statistics for specific agent. Requires authentication."""
    return {
        "users": 0,
        "orders": 0,
        "revenue": 0.0,
    }


# =============================================================================
# User Management Endpoints (Auth required)
# =============================================================================


@admin_router.get("/users", response_model=List[UserResponse])
async def list_users(
    agent_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """Get all users with optional filters. Requires authentication."""
    return []


@admin_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get user by ID. Requires authentication."""
    raise HTTPException(status_code=404, detail="User not found")


@admin_router.get("/users/{user_id}/orders", response_model=List[OrderResponse])
async def get_user_orders(
    user_id: int,
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get orders for specific user. Requires authentication."""
    return []


# =============================================================================
# Order Management Endpoints (Auth required)
# =============================================================================


@admin_router.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    order_status: Optional[str] = None,
    agent_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """Get all orders with optional filters. Requires authentication."""
    return []


@admin_router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get order by ID. Requires authentication."""
    raise HTTPException(status_code=404, detail="Order not found")


@admin_router.get("/orders/{order_id}/tickets")
async def get_order_tickets(
    order_id: int,
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get tickets for specific order. Requires authentication."""
    return []


# =============================================================================
# Dashboard Endpoints (Auth required)
# =============================================================================


@admin_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get dashboard statistics. Requires authentication."""
    return DashboardStats(
        total_users=0,
        total_orders=0,
        total_revenue=0.0,
        active_agents=0,
        orders_today=0,
        revenue_today=0.0,
    )


@admin_router.get("/dashboard/recent-orders")
async def get_recent_orders(
    limit: int = 10,
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get recent orders for dashboard. Requires authentication."""
    return []


@admin_router.get("/dashboard/sales-chart")
async def get_sales_chart(
    period: str = "week",
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get sales chart data. Requires authentication."""
    return {"labels": [], "data": []}
