"""
Admin Panel API Endpoints

Handles authentication, agents, users, orders, dashboard, and webhooks management.
All protected routes require JWT authentication via Bearer token.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import Depends, HTTPException, Request, status
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
    from app.core.rate_limiter import login_rate_limiter
    from app.models import Agent as AgentModel, User as UserModel, Order as OrderModel, Ticket as TicketModel
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
    from backend.app.core.rate_limiter import login_rate_limiter
    from backend.app.models import Agent as AgentModel, User as UserModel, Order as OrderModel, Ticket as TicketModel


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


class TicketResponse(BaseModel):
    id: int
    order_id: int
    bil24_ticket_id: int
    event_name: str
    event_date: datetime
    venue_name: str
    sector: Optional[str]
    row: Optional[str]
    seat: Optional[str]
    price: float
    barcode_number: Optional[str]
    status: str
    sent_to_user: bool
    sent_at: Optional[datetime]

    class Config:
        from_attributes = True


class OrderDetailResponse(BaseModel):
    """Detailed order response with user, agent, and tickets info."""
    id: int
    user_id: int
    user_name: str
    agent_id: int
    agent_name: str
    bil24_order_id: int
    status: str
    total_sum: float
    currency: str
    ticket_count: int
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime]
    tickets: List[TicketResponse]


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
async def admin_login(http_request: Request, request: LoginRequest):
    """Authenticate admin user and return JWT token.

    For development, uses default credentials from settings.
    In production, this should authenticate against the database.

    Rate limited to prevent brute force attacks (5 attempts per minute per IP).
    """
    # Check rate limit before processing login
    rate_limit_error = login_rate_limiter.check_rate_limit(http_request)
    if rate_limit_error:
        raise rate_limit_error

    # Check against default admin credentials (for development)
    # In production, this should check against the database
    if (request.username == settings.ADMIN_DEFAULT_USERNAME and
        request.password == settings.ADMIN_DEFAULT_PASSWORD):
        # Clear rate limit attempts on successful login
        login_rate_limiter.clear_attempts(http_request)
        # Create JWT token
        access_token = create_access_token(
            data={
                "sub": request.username,
                "user_id": 1,
                "role": "super_admin"
            }
        )
        return LoginResponse(access_token=access_token)

    # Record failed attempt and check if limit exceeded
    rate_limit_error = login_rate_limiter.record_attempt(http_request)
    if rate_limit_error:
        raise rate_limit_error

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


class PaginatedAgentsResponse(BaseModel):
    """Paginated response for agents list."""
    agents: List[AgentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@admin_router.get("/agents", response_model=PaginatedAgentsResponse)
async def list_agents(
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all agents with optional search and pagination. Requires authentication."""
    # Build base query
    base_query = select(AgentModel)

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        base_query = base_query.where(
            or_(
                AgentModel.name.ilike(search_pattern),
                func.cast(AgentModel.fid, String).ilike(search_pattern),
            )
        )

    # Get total count before pagination
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate total pages
    total_pages = max(1, (total + page_size - 1) // page_size)

    # Order and paginate
    query = base_query.order_by(AgentModel.id)
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    agents = result.scalars().all()

    return PaginatedAgentsResponse(
        agents=[agent_to_response(agent) for agent in agents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


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


class AgentStatsResponse(BaseModel):
    """Statistics for a specific agent."""
    users: int
    orders: int
    revenue: float


@admin_router.get("/agents/{agent_id}/stats", response_model=AgentStatsResponse)
async def get_agent_stats(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics for specific agent. Requires authentication.

    Returns:
    - users: Count of users whose current_agent_id matches this agent
    - orders: Count of orders associated with this agent
    - revenue: Sum of total_sum for PAID orders associated with this agent
    """
    # Verify agent exists
    agent_result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    if not agent_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    # Count users with this agent as current_agent
    users_result = await db.execute(
        select(func.count(UserModel.id)).where(UserModel.current_agent_id == agent_id)
    )
    users_count = users_result.scalar() or 0

    # Count orders for this agent
    orders_result = await db.execute(
        select(func.count(OrderModel.id)).where(OrderModel.agent_id == agent_id)
    )
    orders_count = orders_result.scalar() or 0

    # Sum revenue from PAID orders for this agent
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(OrderModel.total_sum), 0)).where(
            OrderModel.agent_id == agent_id,
            OrderModel.status == "PAID"
        )
    )
    revenue_total = float(revenue_result.scalar() or 0)

    return AgentStatsResponse(
        users=users_count,
        orders=orders_count,
        revenue=revenue_total,
    )


# =============================================================================
# User Management Endpoints (Auth required)
# =============================================================================


class PaginatedUsersResponse(BaseModel):
    """Paginated response for users list."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@admin_router.get("/users", response_model=PaginatedUsersResponse)
async def list_users(
    agent_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all users with optional filters and pagination. Requires authentication.

    Filters:
    - agent_id: Filter by current agent
    - search: Search in username, first name, last name, or chat_id

    Returns paginated response with total count for accurate page calculation.
    """
    # Build base query for filtering
    base_query = select(UserModel)

    # Apply agent filter
    if agent_id:
        base_query = base_query.where(UserModel.current_agent_id == agent_id)

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        base_query = base_query.where(
            or_(
                UserModel.telegram_username.ilike(search_pattern),
                UserModel.telegram_first_name.ilike(search_pattern),
                UserModel.telegram_last_name.ilike(search_pattern),
                func.cast(UserModel.telegram_chat_id, String).ilike(search_pattern),
            )
        )

    # Get total count before pagination
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate total pages
    total_pages = max(1, (total + page_size - 1) // page_size)

    # Order by created_at descending (newest first)
    query = base_query.order_by(UserModel.created_at.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    return PaginatedUsersResponse(
        users=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


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


class PaginatedOrdersResponse(BaseModel):
    """Paginated response for orders list."""
    orders: List[OrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrderListItem(BaseModel):
    """Order list item with user and agent names."""
    id: int
    user_id: int
    user_name: str
    agent_id: int
    agent_name: str
    bil24_order_id: int
    status: str
    total_sum: float
    ticket_count: int
    created_at: datetime
    paid_at: Optional[datetime]


class PaginatedOrderListResponse(BaseModel):
    """Paginated response for orders list with user/agent names."""
    orders: List[OrderListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


@admin_router.get("/orders", response_model=PaginatedOrderListResponse)
async def list_orders(
    order_status: Optional[str] = None,
    agent_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all orders with optional filters. Requires authentication."""
    from sqlalchemy.orm import joinedload

    # Build base query with relationships
    base_query = select(OrderModel).options(
        joinedload(OrderModel.user),
        joinedload(OrderModel.agent),
    )

    # Apply filters
    if order_status:
        base_query = base_query.where(OrderModel.status == order_status)

    if agent_id:
        base_query = base_query.where(OrderModel.agent_id == agent_id)

    if start_date:
        base_query = base_query.where(OrderModel.created_at >= start_date)

    if end_date:
        base_query = base_query.where(OrderModel.created_at <= end_date)

    if search:
        # Search by order ID or Bill24 order ID
        search_pattern = f"%{search}%"
        base_query = base_query.where(
            or_(
                func.cast(OrderModel.id, String).ilike(search_pattern),
                func.cast(OrderModel.bil24_order_id, String).ilike(search_pattern),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate total pages
    total_pages = max(1, (total + page_size - 1) // page_size)

    # Order and paginate
    query = base_query.order_by(OrderModel.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    orders = result.unique().scalars().all()

    # Build response with user/agent names
    order_items = []
    for order in orders:
        user_name = f"{order.user.telegram_first_name or ''} {order.user.telegram_last_name or ''}".strip()
        if not user_name and order.user.telegram_username:
            user_name = f"@{order.user.telegram_username}"
        elif not user_name:
            user_name = f"User #{order.user_id}"

        order_items.append(OrderListItem(
            id=order.id,
            user_id=order.user_id,
            user_name=user_name,
            agent_id=order.agent_id,
            agent_name=order.agent.name,
            bil24_order_id=order.bil24_order_id,
            status=order.status,
            total_sum=float(order.total_sum),
            ticket_count=order.ticket_count,
            created_at=order.created_at,
            paid_at=order.paid_at,
        ))

    return PaginatedOrderListResponse(
        orders=order_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@admin_router.get("/orders/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get order by ID with full details. Requires authentication."""
    from sqlalchemy.orm import joinedload

    result = await db.execute(
        select(OrderModel)
        .options(
            joinedload(OrderModel.user),
            joinedload(OrderModel.agent),
            joinedload(OrderModel.tickets),
        )
        .where(OrderModel.id == order_id)
    )
    order = result.unique().scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Build user name
    user_name = f"{order.user.telegram_first_name or ''} {order.user.telegram_last_name or ''}".strip()
    if not user_name and order.user.telegram_username:
        user_name = f"@{order.user.telegram_username}"
    elif not user_name:
        user_name = f"User #{order.user_id}"

    # Build tickets response
    tickets = [
        TicketResponse(
            id=ticket.id,
            order_id=ticket.order_id,
            bil24_ticket_id=ticket.bil24_ticket_id,
            event_name=ticket.event_name,
            event_date=ticket.event_date,
            venue_name=ticket.venue_name,
            sector=ticket.sector,
            row=ticket.row,
            seat=ticket.seat,
            price=float(ticket.price),
            barcode_number=ticket.barcode_number,
            status=ticket.status,
            sent_to_user=ticket.sent_to_user,
            sent_at=ticket.sent_at,
        )
        for ticket in order.tickets
    ]

    return OrderDetailResponse(
        id=order.id,
        user_id=order.user_id,
        user_name=user_name,
        agent_id=order.agent_id,
        agent_name=order.agent.name,
        bil24_order_id=order.bil24_order_id,
        status=order.status,
        total_sum=float(order.total_sum),
        currency=order.currency,
        ticket_count=order.ticket_count,
        created_at=order.created_at,
        updated_at=order.updated_at,
        paid_at=order.paid_at,
        tickets=tickets,
    )


@admin_router.get("/orders/{order_id}/tickets", response_model=List[TicketResponse])
async def get_order_tickets(
    order_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get tickets for specific order. Requires authentication."""
    # First verify order exists
    order_result = await db.execute(
        select(OrderModel).where(OrderModel.id == order_id)
    )
    if not order_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Order not found")

    # Get tickets
    result = await db.execute(
        select(TicketModel).where(TicketModel.order_id == order_id)
    )
    tickets = result.scalars().all()

    return [
        TicketResponse(
            id=ticket.id,
            order_id=ticket.order_id,
            bil24_ticket_id=ticket.bil24_ticket_id,
            event_name=ticket.event_name,
            event_date=ticket.event_date,
            venue_name=ticket.venue_name,
            sector=ticket.sector,
            row=ticket.row,
            seat=ticket.seat,
            price=float(ticket.price),
            barcode_number=ticket.barcode_number,
            status=ticket.status,
            sent_to_user=ticket.sent_to_user,
            sent_at=ticket.sent_at,
        )
        for ticket in tickets
    ]


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

    # Get total orders count
    orders_result = await db.execute(select(func.count(OrderModel.id)))
    total_orders = orders_result.scalar() or 0

    # Get total revenue (sum of all order totals)
    revenue_result = await db.execute(select(func.sum(OrderModel.total_sum)))
    total_revenue = float(revenue_result.scalar() or 0)

    # Get today's orders and revenue
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    orders_today_result = await db.execute(
        select(func.count(OrderModel.id)).where(OrderModel.created_at >= today_start)
    )
    orders_today = orders_today_result.scalar() or 0

    revenue_today_result = await db.execute(
        select(func.sum(OrderModel.total_sum)).where(OrderModel.created_at >= today_start)
    )
    revenue_today = float(revenue_today_result.scalar() or 0)

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
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recent orders for dashboard. Requires authentication."""
    # Get recent orders with user and agent info
    result = await db.execute(
        select(OrderModel, UserModel, AgentModel)
        .join(UserModel, OrderModel.user_id == UserModel.id)
        .join(AgentModel, OrderModel.agent_id == AgentModel.id)
        .order_by(OrderModel.created_at.desc())
        .limit(limit)
    )
    orders_data = result.all()

    recent_orders = []
    for order, user, agent in orders_data:
        recent_orders.append({
            "id": order.id,
            "bil24_order_id": order.bil24_order_id,
            "user_name": f"{user.telegram_first_name} {user.telegram_last_name or ''}".strip(),
            "agent_name": agent.name,
            "status": order.status,
            "total_sum": float(order.total_sum),
            "ticket_count": order.ticket_count,
            "created_at": order.created_at.isoformat(),
        })

    return recent_orders


@admin_router.get("/dashboard/sales-chart")
async def get_sales_chart(
    period: str = "week",
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get sales chart data. Requires authentication.

    Returns aggregated orders and revenue data for the specified period.
    Period can be 'week', 'month', or 'year'.
    """
    from datetime import timedelta
    from sqlalchemy import cast, Date

    now = datetime.utcnow()

    # Determine date range based on period
    if period == 'week':
        start_date = now - timedelta(days=7)
        days = 7
        date_format = '%b %d'  # e.g., "Jan 09"
    elif period == 'month':
        start_date = now - timedelta(days=30)
        days = 30
        date_format = '%b %d'
    else:  # year
        start_date = now - timedelta(days=365)
        days = 12  # Group by month
        date_format = '%b'  # e.g., "Jan"

    # Generate all date labels for the period
    labels = []
    data = []

    if period == 'year':
        # Group by month for yearly view
        for i in range(12):
            date = now - timedelta(days=(11-i)*30)
            labels.append(date.strftime('%b'))
            data.append({'orders': 0, 'revenue': 0})
    else:
        # Daily for week/month view
        for i in range(days):
            date = now - timedelta(days=(days-1-i))
            labels.append(date.strftime(date_format))
            data.append({'orders': 0, 'revenue': 0})

    # Query orders from database within the date range
    try:
        result = await db.execute(
            select(
                cast(OrderModel.created_at, Date).label('order_date'),
                func.count(OrderModel.id).label('order_count'),
                func.coalesce(func.sum(OrderModel.total_sum), 0).label('total_revenue')
            )
            .where(OrderModel.created_at >= start_date)
            .group_by(cast(OrderModel.created_at, Date))
            .order_by(cast(OrderModel.created_at, Date))
        )
        orders_by_date = result.all()

        # Map orders to the corresponding date slots
        for row in orders_by_date:
            order_date = row.order_date
            if period == 'year':
                # Find the month slot
                month_label = order_date.strftime('%b')
                for i, label in enumerate(labels):
                    if label == month_label:
                        data[i]['orders'] += int(row.order_count)
                        data[i]['revenue'] += float(row.total_revenue or 0)
                        break
            else:
                # Find the day slot
                date_label = order_date.strftime(date_format)
                for i, label in enumerate(labels):
                    if label == date_label:
                        data[i]['orders'] = int(row.order_count)
                        data[i]['revenue'] = float(row.total_revenue or 0)
                        break
    except Exception as e:
        # Log error but return empty data structure
        print(f"Error fetching sales chart data: {e}")

    return {"labels": labels, "data": data}
