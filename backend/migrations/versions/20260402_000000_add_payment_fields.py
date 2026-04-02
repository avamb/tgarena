"""Add payment fields to agents and orders

Revision ID: 002_payment_fields
Revises: 001_initial
Create Date: 2026-04-02 00:00:00.000000

Adds payment_type to agents, and payment-related fields to orders.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_payment_fields'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add payment_type to agents
    op.add_column(
        'agents',
        sa.Column('payment_type', sa.String(20), server_default='bill24_acquiring', nullable=True),
    )

    # Add payment fields to orders
    op.add_column(
        'orders',
        sa.Column('payment_type', sa.String(20), server_default='bill24_acquiring', nullable=True),
    )
    op.add_column(
        'orders',
        sa.Column('payment_url', sa.Text(), nullable=True),
    )
    op.add_column(
        'orders',
        sa.Column('bil24_form_url', sa.Text(), nullable=True),
    )
    op.add_column(
        'orders',
        sa.Column('reservation_expires_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('orders', 'reservation_expires_at')
    op.drop_column('orders', 'bil24_form_url')
    op.drop_column('orders', 'payment_url')
    op.drop_column('orders', 'payment_type')
    op.drop_column('agents', 'payment_type')
