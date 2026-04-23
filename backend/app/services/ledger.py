"""Ledger posting helpers for agent settlement wallets."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.models import (
        AgentLedgerEntry,
        AgentWallet,
        LedgerDirection,
        LedgerEntryType,
        WalletStatus,
    )
    from app.services.system_settings import get_default_wallet_credit_limit_minor
except ModuleNotFoundError:
    from backend.app.models import (
        AgentLedgerEntry,
        AgentWallet,
        LedgerDirection,
        LedgerEntryType,
        WalletStatus,
    )
    from backend.app.services.system_settings import get_default_wallet_credit_limit_minor

from .money import normalize_currency
from .stripe_connect import build_order_amounts


RESERVE_ENTRY_TYPES = {
    LedgerEntryType.TOP_UP.value,
    LedgerEntryType.RESERVE_HOLD.value,
    LedgerEntryType.RESERVE_RELEASE.value,
}


@dataclass(slots=True)
class LedgerPosting:
    """Normalized input for one ledger write."""

    agent_id: int
    currency: str
    amount_minor: int
    direction: str
    entry_type: str
    order_id: Optional[int] = None
    refund_case_id: Optional[int] = None
    source: str = "system"
    source_id: Optional[str] = None
    description: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _signed_amount(direction: str, amount_minor: int) -> int:
    if direction == LedgerDirection.DEBIT.value:
        return -abs(amount_minor)
    return abs(amount_minor)


def _get_value(data: Any, key: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def build_sale_postings(
    order: Any,
    source: str,
    source_id: str,
) -> list[LedgerPosting]:
    """Build normalized ledger postings for a completed sale."""
    amounts = build_order_amounts(order=order)
    agent_id = int(_get_value(order, "agent_id"))
    currency = str(amounts["currency"])
    ticket_amount_minor = int(amounts["ticket_amount_minor"])
    platform_fee_amount_minor = int(amounts["platform_fee_amount_minor"])
    stripe_fee_estimated_minor = int(_get_value(order, "stripe_fee_estimated_minor", 0) or 0)

    postings = [
        LedgerPosting(
            agent_id=agent_id,
            currency=currency,
            amount_minor=ticket_amount_minor,
            direction=LedgerDirection.CREDIT.value,
            entry_type=LedgerEntryType.SALE.value,
            order_id=int(_get_value(order, "id")),
            source=source,
            source_id=source_id,
            description=f"Sale credit for order #{_get_value(order, 'id')}",
            metadata={
                "gross_amount_minor": int(amounts["gross_amount_minor"]),
                "ticket_amount_minor": ticket_amount_minor,
                "platform_fee_amount_minor": platform_fee_amount_minor,
            },
        )
    ]

    if platform_fee_amount_minor > 0:
        postings.append(
            LedgerPosting(
                agent_id=agent_id,
                currency=currency,
                amount_minor=platform_fee_amount_minor,
                direction=LedgerDirection.CREDIT.value,
                entry_type=LedgerEntryType.PLATFORM_FEE.value,
                order_id=int(_get_value(order, "id")),
                source=source,
                source_id=source_id,
                description=f"Platform fee credit for order #{_get_value(order, 'id')}",
                metadata={
                    "gross_amount_minor": int(amounts["gross_amount_minor"]),
                    "ticket_amount_minor": ticket_amount_minor,
                    "platform_fee_amount_minor": platform_fee_amount_minor,
                },
            )
        )

    if stripe_fee_estimated_minor > 0:
        postings.append(
            LedgerPosting(
                agent_id=agent_id,
                currency=currency,
                amount_minor=stripe_fee_estimated_minor,
                direction=LedgerDirection.DEBIT.value,
                entry_type=LedgerEntryType.STRIPE_FEE_ESTIMATE.value,
                order_id=int(_get_value(order, "id")),
                source=source,
                source_id=source_id,
                description=f"Estimated Stripe fee for order #{_get_value(order, 'id')}",
                metadata={
                    "gross_amount_minor": int(amounts["gross_amount_minor"]),
                    "stripe_fee_estimated_minor": stripe_fee_estimated_minor,
                },
            )
        )

    return postings


def build_refund_postings(
    refund_case: Any,
    source: str,
    source_id: str,
) -> list[LedgerPosting]:
    """Build normalized ledger postings for a completed refund."""
    agent_debit_amount_minor = int(_get_value(refund_case, "agent_debit_amount_minor", 0) or 0)
    platform_cost_amount_minor = int(_get_value(refund_case, "platform_cost_amount_minor", 0) or 0)

    postings: list[LedgerPosting] = []
    if agent_debit_amount_minor > 0:
        postings.append(
            LedgerPosting(
                agent_id=int(_get_value(refund_case, "agent_id")),
                currency=str(_get_value(refund_case, "currency")),
                amount_minor=agent_debit_amount_minor,
                direction=LedgerDirection.DEBIT.value,
                entry_type=LedgerEntryType.REFUND.value,
                order_id=_get_value(refund_case, "order_id"),
                refund_case_id=int(_get_value(refund_case, "id")),
                source=source,
                source_id=source_id,
                description=f"Refund debit for case #{_get_value(refund_case, 'id')}",
                metadata={
                    "customer_refund_amount_minor": int(
                        _get_value(refund_case, "customer_refund_amount_minor", 0) or 0
                    ),
                    "ticket_refund_amount_minor": int(
                        _get_value(refund_case, "ticket_refund_amount_minor", 0) or 0
                    ),
                    "service_fee_refund_amount_minor": int(
                        _get_value(refund_case, "service_fee_refund_amount_minor", 0) or 0
                    ),
                },
            )
        )

    if platform_cost_amount_minor > 0:
        postings.append(
            LedgerPosting(
                agent_id=int(_get_value(refund_case, "agent_id")),
                currency=str(_get_value(refund_case, "currency")),
                amount_minor=platform_cost_amount_minor,
                direction=LedgerDirection.DEBIT.value,
                entry_type=LedgerEntryType.STRIPE_FEE_ACTUAL.value,
                order_id=_get_value(refund_case, "order_id"),
                refund_case_id=int(_get_value(refund_case, "id")),
                source=source,
                source_id=source_id,
                description=f"Refund processing cost for case #{_get_value(refund_case, 'id')}",
                metadata={
                    "platform_cost_amount_minor": platform_cost_amount_minor,
                },
            )
        )

    return postings


def calculate_wallet_state(
    entries: Iterable[AgentLedgerEntry],
    credit_limit_minor: int,
    warning_threshold_minor: int,
    block_threshold_minor: int,
) -> dict[str, int | str]:
    """Compute wallet fields from the ledger."""
    net_minor = 0
    reserve_balance_minor = 0

    for entry in entries:
        signed_amount = _signed_amount(entry.direction, entry.amount_minor)
        net_minor += signed_amount
        if entry.entry_type in RESERVE_ENTRY_TYPES:
            reserve_balance_minor += signed_amount

    reserve_balance_minor = max(0, reserve_balance_minor)
    negative_exposure_minor = max(0, -net_minor)

    if negative_exposure_minor <= 0:
        status = WalletStatus.ACTIVE.value
    elif block_threshold_minor <= 0 or negative_exposure_minor >= block_threshold_minor:
        status = WalletStatus.BLOCKED.value
    elif warning_threshold_minor > 0 and negative_exposure_minor >= warning_threshold_minor:
        status = WalletStatus.WARNING.value
    else:
        status = WalletStatus.ACTIVE.value

    return {
        "reserve_balance_minor": reserve_balance_minor,
        "negative_exposure_minor": negative_exposure_minor,
        "status": status,
        "risk_capacity_minor": reserve_balance_minor + credit_limit_minor - negative_exposure_minor,
        "net_minor": net_minor,
    }


async def get_wallet_for_agent_currency(
    agent_id: int,
    currency: str,
    db: AsyncSession,
) -> Optional[AgentWallet]:
    """Return wallet for an agent/currency pair."""
    normalized_currency = normalize_currency(currency)
    result = await db.execute(
        select(AgentWallet).where(
            AgentWallet.agent_id == agent_id,
            AgentWallet.currency == normalized_currency,
        )
    )
    return result.scalar_one_or_none()


async def ensure_wallet_exists(agent_id: int, currency: str, db: AsyncSession) -> AgentWallet:
    """Get or create a wallet for an agent/currency pair."""
    wallet = await get_wallet_for_agent_currency(agent_id=agent_id, currency=currency, db=db)
    if wallet:
        return wallet

    default_credit_limit_minor = await get_default_wallet_credit_limit_minor(db=db)
    wallet = AgentWallet(
        agent_id=agent_id,
        currency=normalize_currency(currency),
        credit_limit_minor=int(default_credit_limit_minor),
        status=WalletStatus.ACTIVE.value,
    )
    db.add(wallet)
    await db.flush()
    return wallet


async def rebuild_wallet_from_ledger(wallet_id: int, db: AsyncSession) -> AgentWallet:
    """Recompute wallet balances and status from the ledger."""
    wallet_result = await db.execute(select(AgentWallet).where(AgentWallet.id == wallet_id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise ValueError(f"Wallet {wallet_id} not found")

    entries_result = await db.execute(
        select(AgentLedgerEntry).where(AgentLedgerEntry.wallet_id == wallet_id)
    )
    entries = entries_result.scalars().all()

    previous_status = wallet.status
    state = calculate_wallet_state(
        entries=entries,
        credit_limit_minor=wallet.credit_limit_minor,
        warning_threshold_minor=wallet.warning_threshold_minor,
        block_threshold_minor=wallet.block_threshold_minor,
    )

    wallet.reserve_balance_minor = int(state["reserve_balance_minor"])
    wallet.negative_exposure_minor = int(state["negative_exposure_minor"])
    wallet.status = str(state["status"])

    now = datetime.utcnow()
    if wallet.status == WalletStatus.WARNING.value and previous_status != wallet.status:
        wallet.last_warning_at = now
    if wallet.status == WalletStatus.BLOCKED.value and previous_status != wallet.status:
        wallet.last_blocked_at = now

    await db.flush()
    return wallet


async def _find_existing_entry(posting: LedgerPosting, db: AsyncSession) -> Optional[AgentLedgerEntry]:
    if not posting.source or not posting.source_id:
        return None

    result = await db.execute(
        select(AgentLedgerEntry).where(
            AgentLedgerEntry.agent_id == posting.agent_id,
            AgentLedgerEntry.currency == normalize_currency(posting.currency),
            AgentLedgerEntry.source == posting.source,
            AgentLedgerEntry.source_id == posting.source_id,
            AgentLedgerEntry.entry_type == posting.entry_type,
        )
    )
    return result.scalar_one_or_none()


async def _create_entry(
    posting: LedgerPosting,
    db: AsyncSession,
    idempotent: bool,
) -> tuple[AgentLedgerEntry, int, bool]:
    if posting.amount_minor < 0:
        raise ValueError("amount_minor must be non-negative")

    if idempotent:
        existing = await _find_existing_entry(posting=posting, db=db)
        if existing:
            return existing, existing.wallet_id, False

    wallet = await ensure_wallet_exists(agent_id=posting.agent_id, currency=posting.currency, db=db)

    entry = AgentLedgerEntry(
        agent_id=posting.agent_id,
        wallet_id=wallet.id,
        order_id=posting.order_id,
        refund_case_id=posting.refund_case_id,
        currency=normalize_currency(posting.currency),
        amount_minor=posting.amount_minor,
        direction=posting.direction,
        entry_type=posting.entry_type,
        source=posting.source,
        source_id=posting.source_id,
        description=posting.description,
        metadata_json=posting.metadata or {},
    )
    db.add(entry)
    await db.flush()
    return entry, wallet.id, True


async def post_entry(
    posting: LedgerPosting,
    db: AsyncSession,
    idempotent: bool = True,
) -> AgentLedgerEntry:
    """Persist a single ledger entry and recompute its wallet."""
    entry, wallet_id, created = await _create_entry(posting=posting, db=db, idempotent=idempotent)
    if created:
        await rebuild_wallet_from_ledger(wallet_id=wallet_id, db=db)
    return entry


async def post_entries(
    postings: Iterable[LedgerPosting],
    db: AsyncSession,
    idempotent: bool = True,
) -> list[AgentLedgerEntry]:
    """Persist multiple ledger entries and recompute affected wallets once."""
    entries: list[AgentLedgerEntry] = []
    touched_wallet_ids: set[int] = set()

    for posting in postings:
        entry, wallet_id, created = await _create_entry(posting=posting, db=db, idempotent=idempotent)
        entries.append(entry)
        if created:
            touched_wallet_ids.add(wallet_id)

    for wallet_id in touched_wallet_ids:
        await rebuild_wallet_from_ledger(wallet_id=wallet_id, db=db)

    return entries
