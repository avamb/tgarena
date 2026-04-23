"""
Admin Panel API Endpoints

Handles authentication, agents, users, orders, dashboard, and webhooks management.
All protected routes require JWT authentication via Bearer token.
"""

from datetime import datetime, timezone
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
    from app.models import (
        Agent as AgentModel,
        AgentOperationalStatus,
        AgentLedgerEntry as AgentLedgerEntryModel,
        AgentRiskPolicy as AgentRiskPolicyModel,
        AgentWallet as AgentWalletModel,
        Order as OrderModel,
        RefundCase as RefundCaseModel,
        Ticket as TicketModel,
        User as UserModel,
    )
    from app.services import (
        LedgerPosting,
        calculate_refund,
        calculate_remaining_risk_capacity,
        calculate_top_up_required,
        count_refund_events,
        create_order_refund,
        create_pending_refund_case,
        create_onboarding_link,
        create_connected_account,
        ensure_order_charge_id,
        ensure_risk_policy,
        evaluate_agent_risk,
        get_admin_risk_settings,
        get_wallet_for_agent_currency,
        post_entry,
        refresh_account_status,
        save_admin_risk_settings,
    )
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
    from backend.app.models import (
        Agent as AgentModel,
        AgentOperationalStatus,
        AgentLedgerEntry as AgentLedgerEntryModel,
        AgentRiskPolicy as AgentRiskPolicyModel,
        AgentWallet as AgentWalletModel,
        Order as OrderModel,
        RefundCase as RefundCaseModel,
        Ticket as TicketModel,
        User as UserModel,
    )
    from backend.app.services import (
        LedgerPosting,
        calculate_refund,
        calculate_remaining_risk_capacity,
        calculate_top_up_required,
        count_refund_events,
        create_order_refund,
        create_pending_refund_case,
        create_onboarding_link,
        create_connected_account,
        ensure_order_charge_id,
        ensure_risk_policy,
        evaluate_agent_risk,
        get_admin_risk_settings,
        get_wallet_for_agent_currency,
        post_entry,
        refresh_account_status,
        save_admin_risk_settings,
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
    payment_type: str
    agent_operational_status: str
    stripe_account_id: Optional[str]
    stripe_account_status: Optional[str]
    stripe_charges_enabled: bool
    stripe_payouts_enabled: bool
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


class CurrencyBreakdownItem(BaseModel):
    currency: str
    amount: float


class DashboardStats(BaseModel):
    total_users: int
    total_orders: int
    total_revenue: float
    revenue_by_currency: List[CurrencyBreakdownItem]
    active_agents: int
    orders_today: int
    revenue_today: float
    revenue_today_by_currency: List[CurrencyBreakdownItem]


# =============================================================================
# Helper Functions
# =============================================================================


def _utcnow() -> datetime:
    """Return a naive UTC datetime compatible with existing DB columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_public_bot_username() -> str:
    """Return Telegram bot username without a leading @ for public deep links."""
    bot_username = (settings.TELEGRAM_BOT_USERNAME or "ArenaAppTestZone_bot").strip()
    return bot_username.lstrip("@") or "ArenaAppTestZone_bot"


def agent_to_response(agent: AgentModel) -> AgentResponse:
    """Convert Agent model to AgentResponse schema.

    Note: Deep link uses agent.id (NOT fid or token) for identification.
    """
    bot_username = get_public_bot_username()
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        fid=agent.fid,
        zone=agent.zone,
        is_active=agent.is_active,
        payment_type=agent.payment_type,
        agent_operational_status=agent.agent_operational_status,
        stripe_account_id=agent.stripe_account_id,
        stripe_account_status=agent.stripe_account_status,
        stripe_charges_enabled=bool(agent.stripe_charges_enabled),
        stripe_payouts_enabled=bool(agent.stripe_payouts_enabled),
        created_at=agent.created_at,
        deep_link=f"https://t.me/{bot_username}?start=agent_{agent.id}",
    )


def _serialize_currency_breakdown(rows) -> List[CurrencyBreakdownItem]:
    """Normalize aggregated revenue rows into API-friendly currency breakdown."""
    breakdown = []
    for currency, amount in rows:
        breakdown.append(
            CurrencyBreakdownItem(
                currency=currency or "UNK",
                amount=float(amount or 0),
            )
        )
    return breakdown


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


class StripeAccountResponse(BaseModel):
    agent_id: int
    payment_type: str
    stripe_account_id: Optional[str]
    stripe_account_status: Optional[str]
    stripe_charges_enabled: bool
    stripe_payouts_enabled: bool


class StripeOnboardingLinkRequest(BaseModel):
    refresh_url: Optional[str] = None
    return_url: Optional[str] = None


class StripeOnboardingLinkResponse(StripeAccountResponse):
    onboarding_url: str


class AgentStatsResponse(BaseModel):
    """Statistics for a specific agent."""
    users: int
    orders: int
    revenue: float
    revenue_by_currency: List[CurrencyBreakdownItem]


class AgentWalletResponse(BaseModel):
    id: int
    agent_id: int
    currency: str
    reserve_balance_minor: int
    credit_limit_minor: int
    negative_exposure_minor: int
    warning_threshold_minor: int
    block_threshold_minor: int
    status: str
    remaining_risk_capacity_minor: int
    top_up_required_minor: int
    last_warning_at: Optional[datetime]
    last_blocked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AgentWalletListResponse(BaseModel):
    agent_id: int
    agent_operational_status: str
    wallets: List[AgentWalletResponse]


class AgentRiskPolicyResponse(BaseModel):
    agent_id: int
    allow_negative_balance: bool
    auto_block_enabled: bool
    refund_window_days: int
    refund_event_warning_count: int
    refund_event_block_count: int
    rolling_reserve_percent_bps: int
    min_reserve_balance_minor: int
    manual_override_status: Optional[str]
    current_refund_event_count: int
    created_at: datetime
    updated_at: datetime


class AgentRiskPolicyUpdateRequest(BaseModel):
    allow_negative_balance: Optional[bool] = None
    auto_block_enabled: Optional[bool] = None
    refund_window_days: Optional[int] = None
    refund_event_warning_count: Optional[int] = None
    refund_event_block_count: Optional[int] = None
    rolling_reserve_percent_bps: Optional[int] = None
    min_reserve_balance_minor: Optional[int] = None
    manual_override_status: Optional[str] = None


class AgentLedgerEntryResponse(BaseModel):
    id: int
    wallet_id: int
    order_id: Optional[int]
    refund_case_id: Optional[int]
    currency: str
    amount_minor: int
    direction: str
    entry_type: str
    source: str
    source_id: Optional[str]
    description: Optional[str]
    metadata_json: dict
    created_at: datetime


class AgentLedgerResponse(BaseModel):
    agent_id: int
    entries: List[AgentLedgerEntryResponse]


class AgentRiskIncidentResponse(BaseModel):
    id: int
    incident_type: str
    status: str
    currency: str
    amount_minor: int
    order_id: Optional[int]
    refund_case_id: Optional[int]
    reason: Optional[str]
    created_at: datetime


class AgentRiskIncidentListResponse(BaseModel):
    agent_id: int
    refund_event_count: int
    incidents: List[AgentRiskIncidentResponse]


class AgentTopUpRequest(BaseModel):
    currency: str
    amount_minor: int
    description: Optional[str] = None


class AgentTopUpResponse(BaseModel):
    agent_id: int
    entry_id: int
    wallet: AgentWalletResponse


class AgentStatusOverrideResponse(BaseModel):
    agent_id: int
    agent_operational_status: str
    manual_override_status: Optional[str]


class RiskSettingsResponse(BaseModel):
    allow_negative_balance: bool
    auto_block_enabled: bool
    refund_window_days: int
    refund_event_warning_count: int
    refund_event_block_count: int
    rolling_reserve_percent_bps: int
    min_reserve_balance_minor: int
    default_credit_limit_minor: int
    payment_success_url: str
    stripe_connect_return_url: str
    stripe_connect_refresh_url: str
    telegram_bot_username: str
    default_zone: str
    event_cache_ttl: int
    webhook_url: str


class RiskSettingsUpdateRequest(BaseModel):
    allow_negative_balance: Optional[bool] = None
    auto_block_enabled: Optional[bool] = None
    refund_window_days: Optional[int] = None
    refund_event_warning_count: Optional[int] = None
    refund_event_block_count: Optional[int] = None
    rolling_reserve_percent_bps: Optional[int] = None
    min_reserve_balance_minor: Optional[int] = None
    default_credit_limit_minor: Optional[int] = None
    payment_success_url: Optional[str] = None
    stripe_connect_return_url: Optional[str] = None
    stripe_connect_refresh_url: Optional[str] = None
    telegram_bot_username: Optional[str] = None
    default_zone: Optional[str] = None
    event_cache_ttl: Optional[int] = None
    webhook_url: Optional[str] = None


class RefundCalculateRequest(BaseModel):
    mode: str
    reason: Optional[str] = None
    amount_minor: Optional[int] = None


class RefundCalculateResponse(BaseModel):
    order_id: int
    agent_id: int
    currency: str
    customer_refund_amount_minor: int
    ticket_refund_amount_minor: int
    service_fee_refund_amount_minor: int
    platform_cost_amount_minor: int
    agent_debit_amount_minor: int
    post_refund_status: str
    top_up_required_minor: int


class RefundExecuteRequest(RefundCalculateRequest):
    reverse_transfer: bool = True
    refund_application_fee: bool = False


class RefundCaseResponse(BaseModel):
    id: int
    order_id: int
    agent_id: int
    currency: str
    customer_refund_amount_minor: int
    ticket_refund_amount_minor: int
    service_fee_refund_amount_minor: int
    platform_cost_amount_minor: int
    agent_debit_amount_minor: int
    stripe_refund_id: Optional[str]
    status: str
    policy_applied: Optional[str]
    reason: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class RefundExecuteResponse(BaseModel):
    refund_case: RefundCaseResponse
    stripe_refund_status: Optional[str]


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

    revenue_by_currency_result = await db.execute(
        select(
            OrderModel.currency,
            func.coalesce(func.sum(OrderModel.total_sum), 0),
        )
        .where(
            OrderModel.agent_id == agent_id,
            OrderModel.status == "PAID",
        )
        .group_by(OrderModel.currency)
        .order_by(OrderModel.currency)
    )
    revenue_by_currency = _serialize_currency_breakdown(revenue_by_currency_result.all())

    return AgentStatsResponse(
        users=users_count,
        orders=orders_count,
        revenue=revenue_total,
        revenue_by_currency=revenue_by_currency,
    )


def _serialize_stripe_account(agent: AgentModel) -> StripeAccountResponse:
    return StripeAccountResponse(
        agent_id=agent.id,
        payment_type=agent.payment_type,
        stripe_account_id=agent.stripe_account_id,
        stripe_account_status=agent.stripe_account_status,
        stripe_charges_enabled=agent.stripe_charges_enabled,
        stripe_payouts_enabled=agent.stripe_payouts_enabled,
    )


def _serialize_wallet(
    wallet: AgentWalletModel,
    policy: Optional[AgentRiskPolicyModel] = None,
) -> AgentWalletResponse:
    top_up_required_minor = 0
    if policy is not None:
        top_up_required_minor = calculate_top_up_required(wallet=wallet, policy=policy)

    return AgentWalletResponse(
        id=wallet.id,
        agent_id=wallet.agent_id,
        currency=wallet.currency,
        reserve_balance_minor=int(wallet.reserve_balance_minor or 0),
        credit_limit_minor=int(wallet.credit_limit_minor or 0),
        negative_exposure_minor=int(wallet.negative_exposure_minor or 0),
        warning_threshold_minor=int(wallet.warning_threshold_minor or 0),
        block_threshold_minor=int(wallet.block_threshold_minor or 0),
        status=wallet.status,
        remaining_risk_capacity_minor=calculate_remaining_risk_capacity(wallet=wallet),
        top_up_required_minor=top_up_required_minor,
        last_warning_at=wallet.last_warning_at,
        last_blocked_at=wallet.last_blocked_at,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
    )


async def _serialize_risk_policy(
    policy: AgentRiskPolicyModel,
    db: AsyncSession,
) -> AgentRiskPolicyResponse:
    refund_event_count = await count_refund_events(
        agent_id=policy.agent_id,
        window_days=int(policy.refund_window_days or 0),
        db=db,
    )
    return AgentRiskPolicyResponse(
        agent_id=policy.agent_id,
        allow_negative_balance=bool(policy.allow_negative_balance),
        auto_block_enabled=bool(policy.auto_block_enabled),
        refund_window_days=int(policy.refund_window_days or 0),
        refund_event_warning_count=int(policy.refund_event_warning_count or 0),
        refund_event_block_count=int(policy.refund_event_block_count or 0),
        rolling_reserve_percent_bps=int(policy.rolling_reserve_percent_bps or 0),
        min_reserve_balance_minor=int(policy.min_reserve_balance_minor or 0),
        manual_override_status=policy.manual_override_status,
        current_refund_event_count=refund_event_count,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def _serialize_ledger_entry(entry: AgentLedgerEntryModel) -> AgentLedgerEntryResponse:
    return AgentLedgerEntryResponse(
        id=entry.id,
        wallet_id=entry.wallet_id,
        order_id=entry.order_id,
        refund_case_id=entry.refund_case_id,
        currency=entry.currency,
        amount_minor=int(entry.amount_minor or 0),
        direction=entry.direction,
        entry_type=entry.entry_type,
        source=entry.source,
        source_id=entry.source_id,
        description=entry.description,
        metadata_json=entry.metadata_json or {},
        created_at=entry.created_at,
    )


def _serialize_refund_case(refund_case: RefundCaseModel) -> RefundCaseResponse:
    return RefundCaseResponse(
        id=refund_case.id,
        order_id=refund_case.order_id,
        agent_id=refund_case.agent_id,
        currency=refund_case.currency,
        customer_refund_amount_minor=int(refund_case.customer_refund_amount_minor or 0),
        ticket_refund_amount_minor=int(refund_case.ticket_refund_amount_minor or 0),
        service_fee_refund_amount_minor=int(refund_case.service_fee_refund_amount_minor or 0),
        platform_cost_amount_minor=int(refund_case.platform_cost_amount_minor or 0),
        agent_debit_amount_minor=int(refund_case.agent_debit_amount_minor or 0),
        stripe_refund_id=refund_case.stripe_refund_id,
        status=refund_case.status,
        policy_applied=refund_case.policy_applied,
        reason=refund_case.reason,
        created_at=refund_case.created_at,
        completed_at=refund_case.completed_at,
    )


@admin_router.post("/agents/{agent_id}/stripe/account", response_model=StripeAccountResponse)
async def create_agent_stripe_account(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or refresh a Stripe Connect account for an agent."""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        if agent.stripe_account_id:
            await refresh_account_status(agent=agent, db=db)
        else:
            await create_connected_account(agent=agent, db=db)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Stripe account update failed: {exc}") from exc

    return _serialize_stripe_account(agent)


@admin_router.post(
    "/agents/{agent_id}/stripe/onboarding-link",
    response_model=StripeOnboardingLinkResponse,
)
async def create_agent_stripe_onboarding_link(
    agent_id: int,
    payload: StripeOnboardingLinkRequest,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a Stripe onboarding link for an agent."""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.stripe_account_id:
        raise HTTPException(status_code=409, detail="Agent Stripe account is not configured")

    rollout_settings = await get_admin_risk_settings(db=db)
    default_url = str(rollout_settings["payment_success_url"])
    refresh_url = payload.refresh_url or str(rollout_settings["stripe_connect_refresh_url"]) or default_url
    return_url = payload.return_url or str(rollout_settings["stripe_connect_return_url"]) or default_url

    try:
        onboarding_link = create_onboarding_link(
            agent=agent,
            refresh_url=refresh_url,
            return_url=return_url,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Stripe onboarding link failed: {exc}") from exc

    account_response = _serialize_stripe_account(agent).model_dump()
    account_response["onboarding_url"] = onboarding_link.url
    return StripeOnboardingLinkResponse(**account_response)


@admin_router.get("/agents/{agent_id}/stripe/status", response_model=StripeAccountResponse)
async def get_agent_stripe_status(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Refresh and return Stripe Connect account status for an agent."""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.stripe_account_id:
        raise HTTPException(status_code=409, detail="Agent Stripe account is not configured")

    try:
        await refresh_account_status(agent=agent, db=db)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Stripe status refresh failed: {exc}") from exc

    return _serialize_stripe_account(agent)


@admin_router.get("/agents/{agent_id}/wallets", response_model=AgentWalletListResponse)
async def get_agent_wallets(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all settlement wallets for an agent."""
    agent_result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    policy = await ensure_risk_policy(agent_id=agent_id, db=db)
    wallet_result = await db.execute(
        select(AgentWalletModel)
        .where(AgentWalletModel.agent_id == agent_id)
        .order_by(AgentWalletModel.currency)
    )
    wallets = wallet_result.scalars().all()

    return AgentWalletListResponse(
        agent_id=agent_id,
        agent_operational_status=agent.agent_operational_status,
        wallets=[_serialize_wallet(wallet=wallet, policy=policy) for wallet in wallets],
    )


@admin_router.get("/risk/settings", response_model=RiskSettingsResponse)
async def get_risk_settings(
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Return global rollout settings used by risk and payment operations."""
    return RiskSettingsResponse(**(await get_admin_risk_settings(db=db)))


@admin_router.put("/risk/settings", response_model=RiskSettingsResponse)
async def update_risk_settings(
    payload: RiskSettingsUpdateRequest,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist global rollout settings for risk and payment flows."""
    updates = payload.model_dump(exclude_unset=True)
    integer_fields = {
        "refund_window_days",
        "refund_event_warning_count",
        "refund_event_block_count",
        "rolling_reserve_percent_bps",
        "min_reserve_balance_minor",
        "default_credit_limit_minor",
        "event_cache_ttl",
    }
    for field_name in integer_fields:
        if field_name in updates and int(updates[field_name]) < 0:
            raise HTTPException(status_code=400, detail=f"{field_name} must be non-negative")

    if (
        "refund_event_warning_count" in updates
        and "refund_event_block_count" in updates
        and int(updates["refund_event_block_count"]) < int(updates["refund_event_warning_count"])
    ):
        raise HTTPException(
            status_code=400,
            detail="refund_event_block_count must be greater than or equal to refund_event_warning_count",
        )

    if "default_zone" in updates and updates["default_zone"] not in {"test", "real"}:
        raise HTTPException(status_code=400, detail="default_zone must be either 'test' or 'real'")

    saved = await save_admin_risk_settings(db=db, updates=updates)
    return RiskSettingsResponse(**saved)


@admin_router.get("/agents/{agent_id}/risk-policy", response_model=AgentRiskPolicyResponse)
async def get_agent_risk_policy(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Return or initialize the risk policy for one agent."""
    agent_result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    if not agent_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    policy = await ensure_risk_policy(agent_id=agent_id, db=db)
    return await _serialize_risk_policy(policy=policy, db=db)


@admin_router.put("/agents/{agent_id}/risk-policy", response_model=AgentRiskPolicyResponse)
async def update_agent_risk_policy(
    agent_id: int,
    payload: AgentRiskPolicyUpdateRequest,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the per-agent risk policy and rerun the risk engine."""
    agent_result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    policy = await ensure_risk_policy(agent_id=agent_id, db=db)
    updates = payload.model_dump(exclude_unset=True)
    if "manual_override_status" in updates:
        manual_override = updates["manual_override_status"]
        allowed_statuses = {status.value for status in AgentOperationalStatus}
        if manual_override is not None and manual_override not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Unsupported manual_override_status")

    for field_name, value in updates.items():
        setattr(policy, field_name, value)

    wallet_result = await db.execute(
        select(AgentWalletModel)
        .where(AgentWalletModel.agent_id == agent_id)
        .order_by(AgentWalletModel.id)
    )
    wallets = wallet_result.scalars().all()
    for wallet in wallets:
        await evaluate_agent_risk(agent=agent, wallet=wallet, db=db, policy=policy)

    return await _serialize_risk_policy(policy=policy, db=db)


@admin_router.get("/agents/{agent_id}/ledger", response_model=AgentLedgerResponse)
async def get_agent_ledger(
    agent_id: int,
    currency: Optional[str] = None,
    limit: int = 100,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Return recent ledger entries for an agent."""
    agent_result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    if not agent_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    query = (
        select(AgentLedgerEntryModel)
        .where(AgentLedgerEntryModel.agent_id == agent_id)
        .order_by(AgentLedgerEntryModel.created_at.desc(), AgentLedgerEntryModel.id.desc())
        .limit(max(1, min(limit, 500)))
    )
    if currency:
        query = query.where(AgentLedgerEntryModel.currency == currency.upper())

    result = await db.execute(query)
    entries = result.scalars().all()
    return AgentLedgerResponse(
        agent_id=agent_id,
        entries=[_serialize_ledger_entry(entry) for entry in entries],
    )


@admin_router.get("/agents/{agent_id}/risk-incidents", response_model=AgentRiskIncidentListResponse)
async def get_agent_risk_incidents(
    agent_id: int,
    limit: int = 50,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Return refund incidents that currently feed the risk engine."""
    agent_result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    if not agent_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    policy = await ensure_risk_policy(agent_id=agent_id, db=db)
    refund_event_count = await count_refund_events(
        agent_id=agent_id,
        window_days=int(policy.refund_window_days or 0),
        db=db,
    )
    incidents_result = await db.execute(
        select(RefundCaseModel)
        .where(RefundCaseModel.agent_id == agent_id)
        .order_by(RefundCaseModel.created_at.desc(), RefundCaseModel.id.desc())
        .limit(max(1, min(limit, 200)))
    )
    incidents = incidents_result.scalars().all()

    return AgentRiskIncidentListResponse(
        agent_id=agent_id,
        refund_event_count=refund_event_count,
        incidents=[
            AgentRiskIncidentResponse(
                id=incident.id,
                incident_type="refund",
                status=incident.status,
                currency=incident.currency,
                amount_minor=int(incident.agent_debit_amount_minor or 0),
                order_id=incident.order_id,
                refund_case_id=incident.id,
                reason=incident.reason,
                created_at=incident.created_at,
            )
            for incident in incidents
        ],
    )


@admin_router.post("/agents/{agent_id}/topup", response_model=AgentTopUpResponse)
async def top_up_agent_wallet(
    agent_id: int,
    payload: AgentTopUpRequest,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a wallet top-up and rerun the risk engine."""
    if payload.amount_minor <= 0:
        raise HTTPException(status_code=400, detail="amount_minor must be positive")

    agent_result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    entry = await post_entry(
        posting=LedgerPosting(
            agent_id=agent_id,
            currency=payload.currency.upper(),
            amount_minor=int(payload.amount_minor),
            direction="credit",
            entry_type="top_up",
            source="admin_topup",
            source_id=f"agent:{agent_id}:{payload.currency.upper()}:{int(_utcnow().timestamp())}",
            description=payload.description or "Admin top-up",
        ),
        db=db,
        idempotent=False,
    )

    wallet = await get_wallet_for_agent_currency(agent_id=agent_id, currency=payload.currency, db=db)
    if not wallet:
        raise HTTPException(status_code=500, detail="Wallet was not created")

    await evaluate_agent_risk(agent=agent, wallet=wallet, db=db)
    policy = await ensure_risk_policy(agent_id=agent_id, db=db)

    return AgentTopUpResponse(
        agent_id=agent_id,
        entry_id=entry.id,
        wallet=_serialize_wallet(wallet=wallet, policy=policy),
    )


@admin_router.post("/agents/{agent_id}/block", response_model=AgentStatusOverrideResponse)
async def force_block_agent(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Force-block an agent independently of current wallet state."""
    agent_result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    policy = await ensure_risk_policy(agent_id=agent_id, db=db)
    policy.manual_override_status = AgentOperationalStatus.FORCE_BLOCKED.value
    agent.agent_operational_status = AgentOperationalStatus.FORCE_BLOCKED.value

    return AgentStatusOverrideResponse(
        agent_id=agent_id,
        agent_operational_status=agent.agent_operational_status,
        manual_override_status=policy.manual_override_status,
    )


@admin_router.post("/agents/{agent_id}/unblock", response_model=AgentStatusOverrideResponse)
async def unblock_agent(
    agent_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear manual override and recalculate the agent operational status."""
    agent_result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    policy = await ensure_risk_policy(agent_id=agent_id, db=db)
    policy.manual_override_status = None

    wallet_result = await db.execute(
        select(AgentWalletModel)
        .where(AgentWalletModel.agent_id == agent_id)
        .order_by(AgentWalletModel.id)
    )
    wallets = wallet_result.scalars().all()
    if wallets:
        for wallet in wallets:
            await evaluate_agent_risk(agent=agent, wallet=wallet, db=db, policy=policy)
    else:
        agent.agent_operational_status = AgentOperationalStatus.ACTIVE.value

    return AgentStatusOverrideResponse(
        agent_id=agent_id,
        agent_operational_status=agent.agent_operational_status,
        manual_override_status=policy.manual_override_status,
    )


@admin_router.post("/orders/{order_id}/refund/calculate", response_model=RefundCalculateResponse)
async def calculate_order_refund(
    order_id: int,
    payload: RefundCalculateRequest,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Calculate the financial outcome of a refund without calling Stripe."""
    order_result = await db.execute(select(OrderModel).where(OrderModel.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in {"PAID", "REFUNDED"}:
        raise HTTPException(status_code=409, detail="Order is not refundable")

    calculation = await calculate_refund(
        order=order,
        mode=payload.mode,
        reason=payload.reason,
        db=db,
        amount_minor=payload.amount_minor,
    )

    return RefundCalculateResponse(
        order_id=order.id,
        agent_id=order.agent_id,
        currency=order.currency,
        customer_refund_amount_minor=calculation.customer_refund_amount_minor,
        ticket_refund_amount_minor=calculation.ticket_refund_amount_minor,
        service_fee_refund_amount_minor=calculation.service_fee_refund_amount_minor,
        platform_cost_amount_minor=calculation.platform_cost_amount_minor,
        agent_debit_amount_minor=calculation.agent_debit_amount_minor,
        post_refund_status=calculation.post_refund_status,
        top_up_required_minor=calculation.top_up_required_minor,
    )


@admin_router.post("/orders/{order_id}/refund/execute", response_model=RefundExecuteResponse)
async def execute_order_refund(
    order_id: int,
    payload: RefundExecuteRequest,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a refund to Stripe and persist a processing refund case."""
    order_result = await db.execute(select(OrderModel).where(OrderModel.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in {"PAID", "REFUNDED"}:
        raise HTTPException(status_code=409, detail="Order is not refundable")

    calculation = await calculate_refund(
        order=order,
        mode=payload.mode,
        reason=payload.reason,
        db=db,
        amount_minor=payload.amount_minor,
    )
    if calculation.customer_refund_amount_minor <= 0:
        raise HTTPException(status_code=409, detail="Order does not have a refundable balance")

    try:
        await ensure_order_charge_id(order=order, db=db)
        stripe_refund = create_order_refund(
            order=order,
            amount_minor=calculation.customer_refund_amount_minor,
            reason=payload.reason,
            reverse_transfer=payload.reverse_transfer,
            refund_application_fee=payload.refund_application_fee,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Stripe refund failed: {exc}") from exc

    refund_case = await create_pending_refund_case(
        order=order,
        calculation=calculation,
        reason=payload.reason,
        policy_applied=payload.mode,
        stripe_refund_id=getattr(stripe_refund, "id", None),
        db=db,
    )
    order.risk_state = "refund_submitted"

    return RefundExecuteResponse(
        refund_case=_serialize_refund_case(refund_case),
        stripe_refund_status=getattr(stripe_refund, "status", None),
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
    currency: str
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
            currency=order.currency,
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


@admin_router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an order and mark all its tickets as cancelled. Requires authentication."""
    from sqlalchemy.orm import joinedload

    # Get the order with its tickets
    result = await db.execute(
        select(OrderModel)
        .options(joinedload(OrderModel.tickets))
        .where(OrderModel.id == order_id)
    )
    order = result.unique().scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Order is already cancelled")

    # Update order status to CANCELLED
    order.status = "CANCELLED"

    # Update all associated tickets to CANCELLED
    tickets_cancelled = 0
    for ticket in order.tickets:
        if ticket.status != "CANCELLED":
            ticket.status = "CANCELLED"
            tickets_cancelled += 1

    await db.commit()

    return {
        "message": f"Order #{order_id} has been cancelled",
        "order_id": order_id,
        "tickets_cancelled": tickets_cancelled,
    }


@admin_router.delete("/orders/{order_id}")
async def delete_order(
    order_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an order and all its tickets. Requires authentication."""
    from sqlalchemy.orm import joinedload

    # Get the order with its tickets
    result = await db.execute(
        select(OrderModel)
        .options(joinedload(OrderModel.tickets))
        .where(OrderModel.id == order_id)
    )
    order = result.unique().scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Delete all tickets first
    tickets_deleted = len(order.tickets)
    for ticket in order.tickets:
        await db.delete(ticket)

    # Delete the order
    await db.delete(order)
    await db.commit()

    return {
        "message": f"Order #{order_id} and {tickets_deleted} ticket(s) have been deleted",
        "order_id": order_id,
        "tickets_deleted": tickets_deleted,
    }


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


@admin_router.get("/tickets/lookup")
async def lookup_ticket_by_barcode(
    barcode: str,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Look up a ticket by barcode number. Requires authentication."""
    from sqlalchemy.orm import joinedload

    if not barcode or not barcode.strip():
        raise HTTPException(status_code=400, detail="Barcode is required")

    result = await db.execute(
        select(TicketModel)
        .options(joinedload(TicketModel.order))
        .where(TicketModel.barcode_number == barcode.strip())
    )
    ticket = result.unique().scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Get order and user info for the response
    order_result = await db.execute(
        select(OrderModel, UserModel, AgentModel)
        .join(UserModel, OrderModel.user_id == UserModel.id)
        .join(AgentModel, OrderModel.agent_id == AgentModel.id)
        .where(OrderModel.id == ticket.order_id)
    )
    row = order_result.unique().one_or_none()

    if row:
        order, user, agent = row
        user_name = f"{user.telegram_first_name or ''} {user.telegram_last_name or ''}".strip()
        if not user_name and user.telegram_username:
            user_name = f"@{user.telegram_username}"
        elif not user_name:
            user_name = f"User #{user.id}"
    else:
        user_name = "Unknown"
        agent = None

    return {
        "ticket": {
            "id": ticket.id,
            "order_id": ticket.order_id,
            "bil24_ticket_id": ticket.bil24_ticket_id,
            "event_name": ticket.event_name,
            "event_date": ticket.event_date.isoformat() if ticket.event_date else None,
            "venue_name": ticket.venue_name,
            "sector": ticket.sector,
            "row": ticket.row,
            "seat": ticket.seat,
            "price": float(ticket.price),
            "barcode_number": ticket.barcode_number,
            "status": ticket.status,
            "sent_to_user": ticket.sent_to_user,
            "sent_at": ticket.sent_at.isoformat() if ticket.sent_at else None,
        },
        "order": {
            "id": ticket.order.id,
            "status": ticket.order.status,
            "total_sum": float(ticket.order.total_sum),
            "created_at": ticket.order.created_at.isoformat() if ticket.order.created_at else None,
        },
        "user_name": user_name,
        "agent_name": agent.name if agent else "Unknown",
    }


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

    revenue_by_currency_result = await db.execute(
        select(
            OrderModel.currency,
            func.coalesce(func.sum(OrderModel.total_sum), 0),
        )
        .group_by(OrderModel.currency)
        .order_by(OrderModel.currency)
    )
    revenue_by_currency = _serialize_currency_breakdown(revenue_by_currency_result.all())

    # Get today's orders and revenue
    today_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    orders_today_result = await db.execute(
        select(func.count(OrderModel.id)).where(OrderModel.created_at >= today_start)
    )
    orders_today = orders_today_result.scalar() or 0

    revenue_today_result = await db.execute(
        select(func.sum(OrderModel.total_sum)).where(OrderModel.created_at >= today_start)
    )
    revenue_today = float(revenue_today_result.scalar() or 0)

    revenue_today_by_currency_result = await db.execute(
        select(
            OrderModel.currency,
            func.coalesce(func.sum(OrderModel.total_sum), 0),
        )
        .where(OrderModel.created_at >= today_start)
        .group_by(OrderModel.currency)
        .order_by(OrderModel.currency)
    )
    revenue_today_by_currency = _serialize_currency_breakdown(revenue_today_by_currency_result.all())

    return DashboardStats(
        total_users=total_users,
        total_orders=total_orders,
        total_revenue=total_revenue,
        revenue_by_currency=revenue_by_currency,
        active_agents=active_agents,
        orders_today=orders_today,
        revenue_today=revenue_today,
        revenue_today_by_currency=revenue_today_by_currency,
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
            "currency": order.currency,
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

    now = _utcnow()

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


# =============================================================================
# Background Jobs Endpoints
# =============================================================================


class JobEnqueueRequest(BaseModel):
    message: str = "Test job"


class JobStatusResponse(BaseModel):
    job_id: str
    status: Optional[str]
    result: Optional[dict] = None


@admin_router.post("/jobs/test", response_model=JobStatusResponse)
async def enqueue_test_job_endpoint(
    request: JobEnqueueRequest,
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """Enqueue a test background job. Requires authentication."""
    try:
        from app.core.background_jobs import enqueue_test_job
    except ModuleNotFoundError:
        from backend.app.core.background_jobs import enqueue_test_job

    job = await enqueue_test_job(request.message)

    if not job:
        raise HTTPException(status_code=500, detail="Failed to enqueue job")

    return JobStatusResponse(
        job_id=job.job_id,
        status="queued",
    )


@admin_router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status_endpoint(
    job_id: str,
    current_user: AdminUser = Depends(get_current_admin_user),
):
    """Get background job status. Requires authentication."""
    try:
        from app.core.background_jobs import get_job_status, get_job_result
    except ModuleNotFoundError:
        from backend.app.core.background_jobs import get_job_status, get_job_result

    status = await get_job_status(job_id)
    result = None

    if status == "complete":
        result = await get_job_result(job_id)

    return JobStatusResponse(
        job_id=job_id,
        status=status,
        result=result,
    )


# =============================================================================
# Logs Endpoints
# =============================================================================


class LogEntry(BaseModel):
    timestamp: str
    level: str
    logger: str
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    line: Optional[int] = None
    component: Optional[str] = None
    exception: Optional[str] = None


class LogsResponse(BaseModel):
    logs: List[LogEntry]
    total: int
    filters: dict


@admin_router.get("/logs")
async def get_logs(
    lines: int = 100,
    level: Optional[str] = None,
    component: Optional[str] = None,
    search: Optional[str] = None,
    current_user=Depends(get_current_admin_user),
):
    """
    Get recent application logs with optional filtering.

    Query params:
        lines: Number of log entries to return (default 100, max 1000)
        level: Filter by minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        component: Filter by component (bot, api, bill24, system)
        search: Search string to match in log messages
    """
    try:
        from app.core.logging_config import get_log_entries
    except ModuleNotFoundError:
        from backend.app.core.logging_config import get_log_entries

    # Clamp lines to reasonable range
    lines = max(1, min(lines, 1000))

    entries = get_log_entries(
        lines=lines,
        level=level,
        component=component,
        search=search,
    )

    return LogsResponse(
        logs=[LogEntry(**entry) for entry in entries],
        total=len(entries),
        filters={
            "lines": lines,
            "level": level,
            "component": component,
            "search": search,
        },
    )


@admin_router.get("/logs/stream")
async def stream_logs(
    current_user=Depends(get_current_admin_user),
):
    """
    Stream logs in real-time via Server-Sent Events (SSE).

    Returns new log entries as they appear.
    """
    import asyncio
    from starlette.responses import StreamingResponse

    try:
        from app.core.logging_config import get_log_entries
    except ModuleNotFoundError:
        from backend.app.core.logging_config import get_log_entries

    async def event_generator():
        last_timestamp = None
        while True:
            entries = get_log_entries(lines=50)

            new_entries = []
            for entry in entries:
                if last_timestamp and entry["timestamp"] <= last_timestamp:
                    break
                new_entries.append(entry)

            if new_entries:
                last_timestamp = new_entries[0]["timestamp"]
                for entry in reversed(new_entries):
                    yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"

            await asyncio.sleep(2)

    import json
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
