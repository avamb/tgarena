"""
Admin Panel API Endpoints

Handles authentication, agents, users, orders, dashboard, and webhooks management.
All protected routes require JWT authentication via Bearer token.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, or_, func, String
from sqlalchemy.ext.asyncio import AsyncSession

from . import admin_router

try:
    from app.core import (
        settings,
        get_current_admin_user,
        get_password_hash,
        verify_password,
        create_access_token,
        AdminUser,
        get_db,
    )
    from app.models import Agent as AgentModel, User as UserModel
except ModuleNotFoundError:
    from backend.app.core import (
        settings,
        get_current_admin_user,
        get_password_hash,
        verify_password,
        create_access_token,
        AdminUser,
        get_db,
    )
    from backend.app.models import Agent as AgentModel, User as UserModel


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
# Helper Functions
# =============================================================================


def agent_to_response(agent: AgentModel) -> AgentResponse:
    """Convert Agent model to AgentResponse schema.

    Note: Deep link uses agent.id (NOT fid or token) for identification.
    """
    bot_username = settings.TELEGRAM_BOT_USERNAME or "YourBotUsername"
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        fid=agent.fid,
        zone=agent.zone,
        is_active=agent.is_active,
        created_at=agent.created_at,
        deep_link=f"https://t.me/{bot_username}?start=agent_{agent.id}",
    )


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
async def list_agents(
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all agents. Requires authentication."""
    result = await db.execute(select(AgentModel).order_by(AgentModel.id))
    agents = result.scalars().all()
    return [agent_to_response(agent) for agent in agents]


@admin_router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agent by ID. Requires authentication."""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent_to_response(agent)


@admin_router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent: AgentCreate,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create new agent. Requires authentication."""
    # Check if FID already exists
    existing = await db.execute(select(AgentModel).where(AgentModel.fid == agent.fid))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent with FID {agent.fid} already exists",
        )

    # Create new agent
    new_agent = AgentModel(
        name=agent.name,
        fid=agent.fid,
        token=agent.token,  # TODO: Encrypt token before storing
        zone=agent.zone,
        is_active=agent.is_active,
    )
    db.add(new_agent)
    await db.flush()  # Get the ID without committing
    await db.refresh(new_agent)

    return agent_to_response(new_agent)


@admin_router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent: AgentCreate,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update existing agent. Requires authentication."""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    existing_agent = result.scalar_one_or_none()
    if not existing_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if FID is being changed to one that already exists
    if agent.fid != existing_agent.fid:
        fid_check = await db.execute(select(AgentModel).where(AgentModel.fid == agent.fid))
        if fid_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent with FID {agent.fid} already exists",
            )

    # Update agent fields
    existing_agent.name = agent.name
    existing_agent.fid = agent.fid
    existing_agent.token = agent.token  # TODO: Encrypt token
    existing_agent.zone = agent.zone
    existing_agent.is_active = agent.is_active

    await db.flush()
    await db.refresh(existing_agent)

    return agent_to_response(existing_agent)


@admin_router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete agent. Requires authentication."""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await db.delete(agent)
    return {"message": f"Agent '{agent.name}' deleted successfully"}


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
    db: AsyncSession = Depends(get_db),
):
    """Get all users with optional filters. Requires authentication.

    Filters:
    - agent_id: Filter by current agent
    - search: Search in username, first name, last name, or chat_id
    """
    query = select(UserModel)

    # Apply agent filter
    if agent_id:
        query = query.where(UserModel.current_agent_id == agent_id)

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                UserModel.telegram_username.ilike(search_pattern),
                UserModel.telegram_first_name.ilike(search_pattern),
                UserModel.telegram_last_name.ilike(search_pattern),
                func.cast(UserModel.telegram_chat_id, String).ilike(search_pattern),
            )
        )

    # Order by created_at descending (newest first)
    query = query.order_by(UserModel.created_at.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    return users


@admin_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user by ID. Requires authentication."""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


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
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard statistics. Requires authentication."""
    # Get total users count
    users_result = await db.execute(select(func.count(UserModel.id)))
    total_users = users_result.scalar() or 0

    # Get active agents count
    agents_result = await db.execute(
        select(func.count(AgentModel.id)).where(AgentModel.is_active == True)
    )
    active_agents = agents_result.scalar() or 0

    # TODO: Get orders and revenue once Order model is implemented
    total_orders = 0
    total_revenue = 0.0
    orders_today = 0
    revenue_today = 0.0

    return DashboardStats(
        total_users=total_users,
        total_orders=total_orders,
        total_revenue=total_revenue,
        active_agents=active_agents,
        orders_today=orders_today,
        revenue_today=revenue_today,
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
