"""
SQLAlchemy Models for TG-Ticket-Agent

Database models following the schema defined in app_spec.txt.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from app.core.database import Base
except ModuleNotFoundError:
    from backend.app.core.database import Base


class Agent(Base):
    """Ticket agent representing a Bill24 frontend."""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fid: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False)  # Encrypted
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone: Mapped[str] = mapped_column(String(10), default="test")  # 'test' or 'real'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="current_agent")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="agent")
    orders: Mapped[list["Order"]] = relationship(back_populates="agent")


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

    # Relationships
    user: Mapped["User"] = relationship(back_populates="orders")
    agent: Mapped["Agent"] = relationship(back_populates="orders")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="order")


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
    "User",
    "UserSession",
    "Order",
    "Ticket",
    "AdminUser",
    "WebhookLog",
    "SystemSetting",
]
