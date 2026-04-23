"""
SQLAlchemy Models for TG-Ticket-Agent

Database models following the schema defined in app_spec.txt.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from app.core.database import Base
except ModuleNotFoundError:
    from backend.app.core.database import Base


class OrderStatus(str, Enum):
    """Order status enum."""
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class WalletStatus(str, Enum):
    """Wallet operational status."""

    ACTIVE = "active"
    WARNING = "warning"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"


class LedgerDirection(str, Enum):
    """Ledger entry direction."""

    CREDIT = "credit"
    DEBIT = "debit"


class LedgerEntryType(str, Enum):
    """Common ledger entry categories."""

    SALE = "sale"
    PLATFORM_FEE = "platform_fee"
    STRIPE_FEE_ESTIMATE = "stripe_fee_estimate"
    STRIPE_FEE_ACTUAL = "stripe_fee_actual"
    REFUND = "refund"
    RESERVE_HOLD = "reserve_hold"
    RESERVE_RELEASE = "reserve_release"
    PAYOUT = "payout"
    ADJUSTMENT = "adjustment"
    TOP_UP = "top_up"
    CHARGEBACK = "chargeback"


class RefundCaseStatus(str, Enum):
    """Refund case lifecycle status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentOperationalStatus(str, Enum):
    """Agent operational status controlled by the risk engine."""

    ACTIVE = "active"
    WARNING = "warning"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"
    FORCE_BLOCKED = "force_blocked"


class Agent(Base):
    """Ticket agent representing a Bill24 frontend."""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fid: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False)  # Encrypted
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone: Mapped[str] = mapped_column(String(10), default="test")  # 'test' or 'real'
    payment_type: Mapped[str] = mapped_column(
        String(30), default="bill24_acquiring"
    )  # bill24_acquiring, own_acquiring, stripe_connect
    stripe_account_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_account_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    stripe_charges_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    stripe_payouts_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    agent_operational_status: Mapped[str] = mapped_column(
        String(20), default=AgentOperationalStatus.ACTIVE.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="current_agent")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="agent")
    orders: Mapped[list["Order"]] = relationship(back_populates="agent")
    wallets: Mapped[list["AgentWallet"]] = relationship(back_populates="agent")
    risk_policy: Mapped[Optional["AgentRiskPolicy"]] = relationship(
        back_populates="agent",
        uselist=False,
    )
    ledger_entries: Mapped[list["AgentLedgerEntry"]] = relationship(back_populates="agent")
    refund_cases: Mapped[list["RefundCase"]] = relationship(back_populates="agent")


class User(Base):
    """Telegram user who can purchase tickets."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telegram_first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telegram_language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(5), default="ru")
    current_agent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("agents.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    current_agent: Mapped[Optional["Agent"]] = relationship(back_populates="users")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class UserSession(Base):
    """Bill24 session linked to a user and agent."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    bil24_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bil24_session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")
    agent: Mapped["Agent"] = relationship(back_populates="sessions")


class Order(Base):
    """Order for ticket purchase."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    bil24_order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="NEW")  # NEW, PROCESSING, PAID, CANCELLED
    total_sum: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    ticket_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    payment_type: Mapped[str] = mapped_column(String(30), default="bill24_acquiring")
    payment_provider: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    payment_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bil24_form_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reservation_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ticket_amount_minor: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    service_fee_amount_minor: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    gross_amount_minor: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    platform_fee_amount_minor: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    stripe_fee_estimated_minor: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    stripe_fee_actual_minor: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    stripe_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_charge_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_transfer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_application_fee_amount_minor: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    refund_total_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    risk_state: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="orders")
    agent: Mapped["Agent"] = relationship(back_populates="orders")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="order")
    ledger_entries: Mapped[list["AgentLedgerEntry"]] = relationship(back_populates="order")
    refund_cases: Mapped[list["RefundCase"]] = relationship(back_populates="order")


class AgentWallet(Base):
    """Per-agent settlement wallet in minor currency units."""

    __tablename__ = "agent_wallets"
    __table_args__ = (
        UniqueConstraint("agent_id", "currency", name="uq_agent_wallets_agent_currency"),
        Index("ix_agent_wallets_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    reserve_balance_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    credit_limit_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    negative_exposure_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    warning_threshold_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    block_threshold_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(20), default=WalletStatus.ACTIVE.value)
    last_warning_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_blocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    agent: Mapped["Agent"] = relationship(back_populates="wallets")
    ledger_entries: Mapped[list["AgentLedgerEntry"]] = relationship(back_populates="wallet")


class AgentRiskPolicy(Base):
    """Risk policy assigned to an agent."""

    __tablename__ = "agent_risk_policies"
    __table_args__ = (
        UniqueConstraint("agent_id", name="uq_agent_risk_policies_agent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    allow_negative_balance: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_block_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    refund_window_days: Mapped[int] = mapped_column(Integer, default=30)
    refund_event_warning_count: Mapped[int] = mapped_column(Integer, default=3)
    refund_event_block_count: Mapped[int] = mapped_column(Integer, default=7)
    rolling_reserve_percent_bps: Mapped[int] = mapped_column(Integer, default=0)
    min_reserve_balance_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    manual_override_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    agent: Mapped["Agent"] = relationship(back_populates="risk_policy")


class RefundCase(Base):
    """Tracks refund liability and processing status for an order."""

    __tablename__ = "refund_cases"
    __table_args__ = (
        Index("ix_refund_cases_agent_created_at", "agent_id", "created_at"),
        Index("ix_refund_cases_status", "status"),
        Index("ix_refund_cases_order_id", "order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    customer_refund_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    ticket_refund_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    service_fee_refund_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    platform_cost_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    agent_debit_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    stripe_refund_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=RefundCaseStatus.PENDING.value)
    policy_applied: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="refund_cases")
    agent: Mapped["Agent"] = relationship(back_populates="refund_cases")
    ledger_entries: Mapped[list["AgentLedgerEntry"]] = relationship(back_populates="refund_case")


class AgentLedgerEntry(Base):
    """Ledger entry used for settlement and risk accounting."""

    __tablename__ = "agent_ledger_entries"
    __table_args__ = (
        Index("ix_agent_ledger_entries_agent_currency_created_at", "agent_id", "currency", "created_at"),
        Index("ix_agent_ledger_entries_order_id", "order_id"),
        Index("ix_agent_ledger_entries_refund_case_id", "refund_case_id"),
        Index("ix_agent_ledger_entries_entry_type", "entry_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    wallet_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_wallets.id"), nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)
    refund_case_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("refund_cases.id"),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    direction: Mapped[str] = mapped_column(
        String(10),
        default=LedgerDirection.CREDIT.value,
    )
    entry_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent: Mapped["Agent"] = relationship(back_populates="ledger_entries")
    wallet: Mapped["AgentWallet"] = relationship(back_populates="ledger_entries")
    order: Mapped[Optional["Order"]] = relationship(back_populates="ledger_entries")
    refund_case: Mapped[Optional["RefundCase"]] = relationship(back_populates="ledger_entries")


class Ticket(Base):
    """Individual ticket within an order."""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    bil24_ticket_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_name: Mapped[str] = mapped_column(String(500), nullable=False)
    event_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    venue_name: Mapped[str] = mapped_column(String(500), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    row: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    seat: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    qr_code_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Base64
    barcode_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Base64
    barcode_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="VALID")
    sent_to_user: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="tickets")


class AdminUser(Base):
    """Admin panel user."""

    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="super_admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class WebhookLog(Base):
    """Log of webhook calls."""

    __tablename__ = "webhook_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    success: Mapped[bool] = mapped_column(Boolean, default=False)


class SystemSetting(Base):
    """System configuration settings."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


__all__ = [
    "Agent",
    "AgentLedgerEntry",
    "AgentOperationalStatus",
    "AgentRiskPolicy",
    "AgentWallet",
    "User",
    "UserSession",
    "Order",
    "OrderStatus",
    "LedgerDirection",
    "LedgerEntryType",
    "RefundCase",
    "RefundCaseStatus",
    "Ticket",
    "WalletStatus",
    "AdminUser",
    "WebhookLog",
    "SystemSetting",
]
