"""Add agent risk accounting and Stripe Connect schema

Revision ID: 20260421_000001_add_agent_risk_accounting
Revises: 002_payment_fields
Create Date: 2026-04-21 00:00:01.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260421_000001_add_agent_risk_accounting"
down_revision: Union[str, None] = "002_payment_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "agents",
        "payment_type",
        existing_type=sa.String(length=20),
        type_=sa.String(length=30),
        existing_nullable=True,
    )
    op.execute(
        "UPDATE agents SET payment_type = 'bill24_acquiring' WHERE payment_type IS NULL"
    )
    op.alter_column(
        "agents",
        "payment_type",
        existing_type=sa.String(length=30),
        nullable=False,
    )
    op.add_column("agents", sa.Column("stripe_account_id", sa.String(length=255), nullable=True))
    op.add_column(
        "agents",
        sa.Column("stripe_account_status", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column(
            "stripe_charges_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "stripe_payouts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "agent_operational_status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
    )

    op.alter_column(
        "orders",
        "payment_type",
        existing_type=sa.String(length=20),
        type_=sa.String(length=30),
        existing_nullable=True,
    )
    op.execute(
        "UPDATE orders SET payment_type = 'bill24_acquiring' WHERE payment_type IS NULL"
    )
    op.alter_column(
        "orders",
        "payment_type",
        existing_type=sa.String(length=30),
        nullable=False,
    )
    op.add_column("orders", sa.Column("payment_provider", sa.String(length=30), nullable=True))
    op.add_column("orders", sa.Column("ticket_amount_minor", sa.BigInteger(), nullable=True))
    op.add_column("orders", sa.Column("service_fee_amount_minor", sa.BigInteger(), nullable=True))
    op.add_column("orders", sa.Column("gross_amount_minor", sa.BigInteger(), nullable=True))
    op.add_column("orders", sa.Column("platform_fee_amount_minor", sa.BigInteger(), nullable=True))
    op.add_column(
        "orders",
        sa.Column("stripe_fee_estimated_minor", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("stripe_fee_actual_minor", sa.BigInteger(), nullable=True),
    )
    op.add_column("orders", sa.Column("stripe_session_id", sa.String(length=255), nullable=True))
    op.add_column(
        "orders",
        sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
    )
    op.add_column("orders", sa.Column("stripe_charge_id", sa.String(length=255), nullable=True))
    op.add_column("orders", sa.Column("stripe_transfer_id", sa.String(length=255), nullable=True))
    op.add_column(
        "orders",
        sa.Column(
            "stripe_application_fee_amount_minor",
            sa.BigInteger(),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "refund_total_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("orders", sa.Column("risk_state", sa.String(length=30), nullable=True))

    op.create_table(
        "agent_wallets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "reserve_balance_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "credit_limit_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "negative_exposure_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "warning_threshold_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "block_threshold_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
        sa.Column("last_warning_at", sa.DateTime(), nullable=True),
        sa.Column("last_blocked_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "currency", name="uq_agent_wallets_agent_currency"),
    )
    op.create_index("ix_agent_wallets_status", "agent_wallets", ["status"], unique=False)

    op.create_table(
        "agent_risk_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column(
            "allow_negative_balance",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "auto_block_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "refund_window_days",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
        sa.Column(
            "refund_event_warning_count",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
        sa.Column(
            "refund_event_block_count",
            sa.Integer(),
            nullable=False,
            server_default="7",
        ),
        sa.Column(
            "rolling_reserve_percent_bps",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "min_reserve_balance_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("manual_override_status", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", name="uq_agent_risk_policies_agent_id"),
    )

    op.create_table(
        "refund_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "customer_refund_amount_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "ticket_refund_amount_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "service_fee_refund_amount_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "platform_cost_amount_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "agent_debit_amount_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("stripe_refund_id", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("policy_applied", sa.String(length=50), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_refund_cases_agent_created_at",
        "refund_cases",
        ["agent_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_refund_cases_status", "refund_cases", ["status"], unique=False)
    op.create_index("ix_refund_cases_order_id", "refund_cases", ["order_id"], unique=False)

    op.create_table(
        "agent_ledger_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("refund_case_id", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("entry_type", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["wallet_id"], ["agent_wallets.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["refund_case_id"], ["refund_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_ledger_entries_agent_currency_created_at",
        "agent_ledger_entries",
        ["agent_id", "currency", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_agent_ledger_entries_order_id",
        "agent_ledger_entries",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_ledger_entries_refund_case_id",
        "agent_ledger_entries",
        ["refund_case_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_ledger_entries_entry_type",
        "agent_ledger_entries",
        ["entry_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_ledger_entries_entry_type", table_name="agent_ledger_entries")
    op.drop_index("ix_agent_ledger_entries_refund_case_id", table_name="agent_ledger_entries")
    op.drop_index("ix_agent_ledger_entries_order_id", table_name="agent_ledger_entries")
    op.drop_index(
        "ix_agent_ledger_entries_agent_currency_created_at",
        table_name="agent_ledger_entries",
    )
    op.drop_table("agent_ledger_entries")

    op.drop_index("ix_refund_cases_order_id", table_name="refund_cases")
    op.drop_index("ix_refund_cases_status", table_name="refund_cases")
    op.drop_index("ix_refund_cases_agent_created_at", table_name="refund_cases")
    op.drop_table("refund_cases")

    op.drop_table("agent_risk_policies")

    op.drop_index("ix_agent_wallets_status", table_name="agent_wallets")
    op.drop_table("agent_wallets")

    op.drop_column("orders", "risk_state")
    op.drop_column("orders", "refund_total_minor")
    op.drop_column("orders", "stripe_application_fee_amount_minor")
    op.drop_column("orders", "stripe_transfer_id")
    op.drop_column("orders", "stripe_charge_id")
    op.drop_column("orders", "stripe_payment_intent_id")
    op.drop_column("orders", "stripe_session_id")
    op.drop_column("orders", "stripe_fee_actual_minor")
    op.drop_column("orders", "stripe_fee_estimated_minor")
    op.drop_column("orders", "platform_fee_amount_minor")
    op.drop_column("orders", "gross_amount_minor")
    op.drop_column("orders", "service_fee_amount_minor")
    op.drop_column("orders", "ticket_amount_minor")
    op.drop_column("orders", "payment_provider")
    op.alter_column(
        "orders",
        "payment_type",
        existing_type=sa.String(length=30),
        type_=sa.String(length=20),
        existing_nullable=False,
        nullable=True,
    )

    op.drop_column("agents", "agent_operational_status")
    op.drop_column("agents", "stripe_payouts_enabled")
    op.drop_column("agents", "stripe_charges_enabled")
    op.drop_column("agents", "stripe_account_status")
    op.drop_column("agents", "stripe_account_id")
    op.alter_column(
        "agents",
        "payment_type",
        existing_type=sa.String(length=30),
        type_=sa.String(length=20),
        existing_nullable=False,
        nullable=True,
    )
