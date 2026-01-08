"""
Admin Panel API Endpoints

Handles authentication, agents, users, orders, dashboard, and webhooks management.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from . import admin_router


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
# Authentication Endpoints
# =============================================================================


@admin_router.post("/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    """Authenticate admin user and return JWT token."""
    # TODO: Implement actual authentication
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication not yet implemented",
    )


@admin_router.post("/refresh")
async def refresh_token():
    """Refresh JWT token."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not yet implemented",
    )


@admin_router.post("/logout")
async def admin_logout():
    """Logout admin user."""
    return {"message": "Logged out successfully"}


# =============================================================================
# Agent Management Endpoints
# =============================================================================


@admin_router.get("/agents", response_model=List[AgentResponse])
async def list_agents():
    """Get all agents."""
    # TODO: Implement
    return []


@admin_router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int):
    """Get agent by ID."""
    raise HTTPException(status_code=404, detail="Agent not found")


@admin_router.post("/agents", response_model=AgentResponse)
async def create_agent(agent: AgentCreate):
    """Create new agent."""
    # TODO: Implement
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Agent creation not yet implemented",
    )


@admin_router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, agent: AgentCreate):
    """Update existing agent."""
    raise HTTPException(status_code=404, detail="Agent not found")


@admin_router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: int):
    """Delete agent."""
    raise HTTPException(status_code=404, detail="Agent not found")


@admin_router.get("/agents/{agent_id}/stats")
async def get_agent_stats(agent_id: int):
    """Get statistics for specific agent."""
    return {
        "users": 0,
        "orders": 0,
        "revenue": 0.0,
    }


# =============================================================================
# User Management Endpoints
# =============================================================================


@admin_router.get("/users", response_model=List[UserResponse])
async def list_users(
    agent_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    """Get all users with optional filters."""
    return []


@admin_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """Get user by ID."""
    raise HTTPException(status_code=404, detail="User not found")


@admin_router.get("/users/{user_id}/orders", response_model=List[OrderResponse])
async def get_user_orders(user_id: int):
    """Get orders for specific user."""
    return []


# =============================================================================
# Order Management Endpoints
# =============================================================================


@admin_router.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    status: Optional[str] = None,
    agent_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
):
    """Get all orders with optional filters."""
    return []


@admin_router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int):
    """Get order by ID."""
    raise HTTPException(status_code=404, detail="Order not found")


@admin_router.get("/orders/{order_id}/tickets")
async def get_order_tickets(order_id: int):
    """Get tickets for specific order."""
    return []


# =============================================================================
# Dashboard Endpoints
# =============================================================================


@admin_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics."""
    return DashboardStats(
        total_users=0,
        total_orders=0,
        total_revenue=0.0,
        active_agents=0,
        orders_today=0,
        revenue_today=0.0,
    )


@admin_router.get("/dashboard/recent-orders")
async def get_recent_orders(limit: int = 10):
    """Get recent orders for dashboard."""
    return []


@admin_router.get("/dashboard/sales-chart")
async def get_sales_chart(period: str = "week"):
    """Get sales chart data."""
    return {"labels": [], "data": []}
