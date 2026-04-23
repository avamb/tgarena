"""Refund calculation and ledger application helpers."""

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.models import Agent, Order, RefundCase, RefundCaseStatus
except ModuleNotFoundError:
    from backend.app.models import Agent, Order, RefundCase, RefundCaseStatus

from .ledger import build_refund_postings, get_wallet_for_agent_currency, post_entries
from .risk_engine import (
    calculate_top_up_required,
    count_refund_events,
    ensure_risk_policy,
    evaluate_agent_risk,
    evaluate_wallet_status,
)
from .stripe_connect import build_order_amounts


def _utcnow() -> datetime:
    """Return a naive UTC datetime compatible with existing DB columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(slots=True)
class RefundCalculation:
    """Refund amount breakdown for one order."""

    customer_refund_amount_minor: int
    ticket_refund_amount_minor: int
    service_fee_refund_amount_minor: int
    platform_cost_amount_minor: int
    agent_debit_amount_minor: int
    post_refund_status: str
    top_up_required_minor: int


def _remaining_component_amounts(order: Order) -> tuple[int, int]:
    amounts = build_order_amounts(order=order)
    ticket_total_minor = int(amounts["ticket_amount_minor"])
    service_fee_total_minor = int(amounts["gross_amount_minor"]) - ticket_total_minor
    already_refunded_minor = int(order.refund_total_minor or 0)

    refunded_ticket_minor = min(already_refunded_minor, ticket_total_minor)
    refunded_service_fee_minor = max(0, already_refunded_minor - refunded_ticket_minor)

    return (
        max(0, ticket_total_minor - refunded_ticket_minor),
        max(0, service_fee_total_minor - refunded_service_fee_minor),
    )


async def calculate_refund(
    order: Order,
    mode: str,
    reason: Optional[str],
    db: AsyncSession,
    amount_minor: Optional[int] = None,
) -> RefundCalculation:
    """Calculate a refund breakdown without executing it in Stripe."""
    remaining_ticket_minor, remaining_service_fee_minor = _remaining_component_amounts(order)
    remaining_total_minor = remaining_ticket_minor + remaining_service_fee_minor

    if mode == "full_refund":
        customer_refund_amount_minor = remaining_total_minor
        ticket_refund_amount_minor = remaining_ticket_minor
        service_fee_refund_amount_minor = remaining_service_fee_minor
    elif mode == "ticket_only_refund":
        customer_refund_amount_minor = remaining_ticket_minor
        ticket_refund_amount_minor = remaining_ticket_minor
        service_fee_refund_amount_minor = 0
    elif mode == "custom_partial_refund":
        if amount_minor is None:
            raise ValueError("amount_minor is required for custom_partial_refund")
        customer_refund_amount_minor = max(0, min(int(amount_minor), remaining_total_minor))
        ticket_refund_amount_minor = min(customer_refund_amount_minor, remaining_ticket_minor)
        service_fee_refund_amount_minor = max(
            0,
            customer_refund_amount_minor - ticket_refund_amount_minor,
        )
    else:
        raise ValueError(f"Unsupported refund mode: {mode}")

    agent_id = getattr(order, "agent_id", None)
    can_project_risk = agent_id is not None and hasattr(db, "execute")
    policy = None
    wallet = None
    if can_project_risk:
        policy = await ensure_risk_policy(agent_id=agent_id, db=db)
        wallet = await get_wallet_for_agent_currency(
            agent_id=agent_id,
            currency=order.currency,
            db=db,
        )

    projected_status = "pending"
    top_up_required_minor = 0
    if wallet and policy:
        projected_negative_exposure_minor = (
            int(wallet.negative_exposure_minor or 0)
            + customer_refund_amount_minor
        )
        projected_wallet_status = wallet.status
        if projected_negative_exposure_minor <= 0:
            projected_wallet_status = "active"
        elif int(wallet.block_threshold_minor or 0) <= 0 or (
            projected_negative_exposure_minor >= int(wallet.block_threshold_minor or 0)
        ):
            projected_wallet_status = "blocked"
        elif int(wallet.warning_threshold_minor or 0) > 0 and (
            projected_negative_exposure_minor >= int(wallet.warning_threshold_minor or 0)
        ):
            projected_wallet_status = "warning"

        projected_wallet = SimpleNamespace(
            id=wallet.id,
            agent_id=wallet.agent_id,
            currency=wallet.currency,
            reserve_balance_minor=int(wallet.reserve_balance_minor or 0),
            credit_limit_minor=int(wallet.credit_limit_minor or 0),
            negative_exposure_minor=projected_negative_exposure_minor,
            warning_threshold_minor=int(wallet.warning_threshold_minor or 0),
            block_threshold_minor=int(wallet.block_threshold_minor or 0),
            status=projected_wallet_status,
        )
        projected_status = evaluate_wallet_status(
            wallet=projected_wallet,
            policy=policy,
            refund_event_count=(
                await count_refund_events(
                    agent_id=agent_id,
                    window_days=int(policy.refund_window_days or 0),
                    db=db,
                )
            )
            + (1 if customer_refund_amount_minor > 0 else 0),
        )
        top_up_required_minor = calculate_top_up_required(
            wallet=projected_wallet,
            policy=policy,
        )

    return RefundCalculation(
        customer_refund_amount_minor=customer_refund_amount_minor,
        ticket_refund_amount_minor=ticket_refund_amount_minor,
        service_fee_refund_amount_minor=service_fee_refund_amount_minor,
        platform_cost_amount_minor=0,
        agent_debit_amount_minor=customer_refund_amount_minor,
        post_refund_status=projected_status,
        top_up_required_minor=top_up_required_minor,
    )


async def create_pending_refund_case(
    order: Order,
    calculation: RefundCalculation,
    reason: Optional[str],
    policy_applied: Optional[str],
    stripe_refund_id: Optional[str],
    db: AsyncSession,
) -> RefundCase:
    """Create a pending refund case before webhook confirmation arrives."""
    refund_case = RefundCase(
        order_id=order.id,
        agent_id=order.agent_id,
        currency=order.currency,
        customer_refund_amount_minor=int(calculation.customer_refund_amount_minor),
        ticket_refund_amount_minor=int(calculation.ticket_refund_amount_minor),
        service_fee_refund_amount_minor=int(calculation.service_fee_refund_amount_minor),
        platform_cost_amount_minor=int(calculation.platform_cost_amount_minor),
        agent_debit_amount_minor=int(calculation.agent_debit_amount_minor),
        stripe_refund_id=stripe_refund_id,
        status=RefundCaseStatus.PROCESSING.value,
        policy_applied=policy_applied,
        reason=reason,
    )
    db.add(refund_case)
    await db.flush()
    return refund_case


async def create_refund_case_from_webhook(
    order: Order,
    refund_amount_minor: int,
    stripe_refund_id: Optional[str],
    reason: Optional[str],
    db: AsyncSession,
) -> RefundCase:
    """Create a completed refund case from a Stripe refund webhook delta."""
    if refund_amount_minor <= 0:
        raise ValueError("refund_amount_minor must be positive")

    existing_refund_case = None
    if stripe_refund_id and hasattr(db, "execute"):
        result = await db.execute(
            select(RefundCase).where(RefundCase.stripe_refund_id == stripe_refund_id)
        )
        existing_refund_case = result.scalar_one_or_none()

    remaining_ticket_minor, remaining_service_fee_minor = _remaining_component_amounts(order)
    ticket_refund_amount_minor = min(int(refund_amount_minor), remaining_ticket_minor)
    service_fee_refund_amount_minor = min(
        max(0, int(refund_amount_minor) - ticket_refund_amount_minor),
        remaining_service_fee_minor,
    )

    refund_case = existing_refund_case or RefundCase(
        order_id=order.id,
        agent_id=order.agent_id,
        currency=order.currency,
    )
    refund_case.customer_refund_amount_minor = int(refund_amount_minor)
    refund_case.ticket_refund_amount_minor = ticket_refund_amount_minor
    refund_case.service_fee_refund_amount_minor = service_fee_refund_amount_minor
    refund_case.platform_cost_amount_minor = 0
    refund_case.agent_debit_amount_minor = int(refund_amount_minor)
    refund_case.stripe_refund_id = stripe_refund_id
    refund_case.status = RefundCaseStatus.COMPLETED.value
    refund_case.reason = reason
    refund_case.completed_at = _utcnow()

    if existing_refund_case is None:
        db.add(refund_case)
    await db.flush()
    return refund_case


def build_agent_debit_entries(
    refund_case: RefundCase,
    source: str,
    source_id: str,
) -> list:
    """Build refund debit postings for a completed refund case."""
    return build_refund_postings(
        refund_case=refund_case,
        source=source,
        source_id=source_id,
    )


async def apply_refund_outcome(
    refund_case: RefundCase,
    db: AsyncSession,
    source: str,
    source_id: str,
) -> list:
    """Write refund ledger entries, recompute wallet, and rerun risk evaluation."""
    entries = await post_entries(
        postings=build_agent_debit_entries(
            refund_case=refund_case,
            source=source,
            source_id=source_id,
        ),
        db=db,
        idempotent=True,
    )

    wallet = await get_wallet_for_agent_currency(
        agent_id=refund_case.agent_id,
        currency=refund_case.currency,
        db=db,
    )
    if wallet:
        agent_result = await db.execute(select(Agent).where(Agent.id == refund_case.agent_id))
        agent = agent_result.scalar_one_or_none()
        if agent:
            await evaluate_agent_risk(agent=agent, wallet=wallet, db=db)

    return entries


async def execute_refund(refund_case_id: int, db: AsyncSession) -> RefundCase:
    """Finalize a prepared refund case inside local accounting."""
    result = await db.execute(select(RefundCase).where(RefundCase.id == refund_case_id))
    refund_case = result.scalar_one_or_none()
    if not refund_case:
        raise ValueError(f"Refund case {refund_case_id} not found")

    await apply_refund_outcome(
        refund_case=refund_case,
        db=db,
        source="refund_case",
        source_id=f"refund_case:{refund_case.id}",
    )
    refund_case.status = RefundCaseStatus.COMPLETED.value
    refund_case.completed_at = refund_case.completed_at or _utcnow()
    await db.flush()
    return refund_case
