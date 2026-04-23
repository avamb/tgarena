"""Risk evaluation helpers for ledger-backed agent wallets."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.models import (
        Agent,
        AgentOperationalStatus,
        AgentRiskPolicy,
        AgentWallet,
        RefundCase,
        RefundCaseStatus,
        WalletStatus,
    )
    from app.services.system_settings import get_risk_policy_defaults
except ModuleNotFoundError:
    from backend.app.models import (
        Agent,
        AgentOperationalStatus,
        AgentRiskPolicy,
        AgentWallet,
        RefundCase,
        RefundCaseStatus,
        WalletStatus,
    )
    from backend.app.services.system_settings import get_risk_policy_defaults


@dataclass(slots=True)
class RiskEvaluation:
    """Compact risk decision output."""

    agent_id: int
    wallet_id: Optional[int]
    currency: Optional[str]
    status: str
    wallet_status_before: Optional[str]
    wallet_status_after: Optional[str]
    refund_event_count: int
    remaining_risk_capacity_minor: int
    top_up_required_minor: int
    money_threshold_hit: bool
    event_threshold_hit: bool


async def ensure_risk_policy(agent_id: int, db: AsyncSession) -> AgentRiskPolicy:
    """Get or create a default risk policy for an agent."""
    result = await db.execute(
        select(AgentRiskPolicy).where(AgentRiskPolicy.agent_id == agent_id)
    )
    policy = result.scalar_one_or_none()
    if policy:
        return policy

    defaults = await get_risk_policy_defaults(db=db)
    policy = AgentRiskPolicy(
        agent_id=agent_id,
        allow_negative_balance=bool(defaults["allow_negative_balance"]),
        auto_block_enabled=bool(defaults["auto_block_enabled"]),
        refund_window_days=int(defaults["refund_window_days"]),
        refund_event_warning_count=int(defaults["refund_event_warning_count"]),
        refund_event_block_count=int(defaults["refund_event_block_count"]),
        rolling_reserve_percent_bps=int(defaults["rolling_reserve_percent_bps"]),
        min_reserve_balance_minor=int(defaults["min_reserve_balance_minor"]),
    )
    db.add(policy)
    await db.flush()
    return policy


async def count_refund_events(agent_id: int, window_days: int, db: AsyncSession) -> int:
    """Count completed refund incidents within the configured rolling window."""
    cutoff = datetime.utcnow() - timedelta(days=max(window_days, 0))
    result = await db.execute(
        select(func.count(RefundCase.id)).where(
            RefundCase.agent_id == agent_id,
            RefundCase.status == RefundCaseStatus.COMPLETED.value,
            RefundCase.created_at >= cutoff,
        )
    )
    return int(result.scalar() or 0)


def calculate_remaining_risk_capacity(wallet: AgentWallet) -> int:
    """Return current remaining wallet risk capacity."""
    return (
        int(wallet.reserve_balance_minor or 0)
        + int(wallet.credit_limit_minor or 0)
        - int(wallet.negative_exposure_minor or 0)
    )


def calculate_top_up_required(wallet: AgentWallet, policy: AgentRiskPolicy) -> int:
    """Return the minimum extra funding needed to satisfy current constraints."""
    remaining_capacity = calculate_remaining_risk_capacity(wallet)
    min_reserve_shortfall = max(
        0,
        int(policy.min_reserve_balance_minor or 0) - int(wallet.reserve_balance_minor or 0),
    )
    capacity_shortfall = max(0, -remaining_capacity)
    return max(min_reserve_shortfall, capacity_shortfall)


def should_block_agent(
    wallet: AgentWallet,
    policy: AgentRiskPolicy,
    refund_event_count: int,
) -> bool:
    """Return True when the agent should be blocked."""
    if wallet.status == WalletStatus.BLOCKED.value:
        return True

    if not bool(policy.allow_negative_balance) and int(wallet.negative_exposure_minor or 0) > 0:
        return True

    block_limit = int(policy.refund_event_block_count or 0)
    if block_limit > 0 and refund_event_count >= block_limit:
        return True

    return False


def should_warn_agent(
    wallet: AgentWallet,
    policy: AgentRiskPolicy,
    refund_event_count: int,
) -> bool:
    """Return True when the agent should be moved into a warning state."""
    if wallet.status == WalletStatus.WARNING.value:
        return True

    warning_limit = int(policy.refund_event_warning_count or 0)
    if warning_limit > 0 and refund_event_count >= warning_limit:
        return True

    return False


def evaluate_wallet_status(
    wallet: AgentWallet,
    policy: AgentRiskPolicy,
    refund_event_count: int,
) -> str:
    """Resolve the operational status for an agent from wallet and policy state."""
    manual_override = getattr(policy, "manual_override_status", None)
    if manual_override:
        return str(manual_override)

    if should_block_agent(wallet=wallet, policy=policy, refund_event_count=refund_event_count):
        if bool(policy.auto_block_enabled):
            return AgentOperationalStatus.BLOCKED.value
        return AgentOperationalStatus.RESTRICTED.value

    if wallet.status == WalletStatus.RESTRICTED.value:
        return AgentOperationalStatus.RESTRICTED.value

    if should_warn_agent(wallet=wallet, policy=policy, refund_event_count=refund_event_count):
        return AgentOperationalStatus.WARNING.value

    return AgentOperationalStatus.ACTIVE.value


async def apply_agent_status(
    agent: Agent,
    wallet: AgentWallet,
    status: str,
    db: AsyncSession,
) -> Agent:
    """Persist agent operational status derived by the risk engine."""
    agent.agent_operational_status = status
    agent.updated_at = datetime.utcnow()
    await db.flush()
    return agent


async def evaluate_agent_risk(
    agent: Agent,
    wallet: AgentWallet,
    db: AsyncSession,
    policy: Optional[AgentRiskPolicy] = None,
) -> RiskEvaluation:
    """Run the minimal risk engine for one agent wallet."""
    policy = policy or await ensure_risk_policy(agent_id=agent.id, db=db)
    refund_event_count = await count_refund_events(
        agent_id=agent.id,
        window_days=int(policy.refund_window_days or 0),
        db=db,
    )

    wallet_status_before = getattr(agent, "agent_operational_status", None)
    status = evaluate_wallet_status(
        wallet=wallet,
        policy=policy,
        refund_event_count=refund_event_count,
    )
    await apply_agent_status(agent=agent, wallet=wallet, status=status, db=db)

    remaining_capacity = calculate_remaining_risk_capacity(wallet)
    warning_limit = int(policy.refund_event_warning_count or 0)
    block_limit = int(policy.refund_event_block_count or 0)

    return RiskEvaluation(
        agent_id=agent.id,
        wallet_id=wallet.id,
        currency=wallet.currency,
        status=status,
        wallet_status_before=wallet_status_before,
        wallet_status_after=status,
        refund_event_count=refund_event_count,
        remaining_risk_capacity_minor=remaining_capacity,
        top_up_required_minor=calculate_top_up_required(wallet=wallet, policy=policy),
        money_threshold_hit=remaining_capacity < 0 or wallet.status in {
            WalletStatus.WARNING.value,
            WalletStatus.BLOCKED.value,
        },
        event_threshold_hit=(block_limit > 0 and refund_event_count >= block_limit)
        or (warning_limit > 0 and refund_event_count >= warning_limit),
    )
