"""Initial database schema

Revision ID: 001_initial
Revises:
Create Date: 2025-01-09 00:00:00.000000

Creates all tables defined in app_spec.txt:
- agents: Ticket agents with Bill24 credentials
- users: Telegram users
- user_sessions: Bill24 sessions linked to users
- orders: Ticket orders
- tickets: Individual tickets
- admin_users: Admin panel users
- webhook_logs: Webhook call logs
- system_settings: System configuration
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all database tables."""

    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fid', sa.BigInteger(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('zone', sa.String(length=10), nullable=True, server_default='test'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fid')
    )
    op.create_index('ix_agents_fid', 'agents', ['fid'], unique=True)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_username', sa.String(length=255), nullable=True),
        sa.Column('telegram_first_name', sa.String(length=255), nullable=False),
        sa.Column('telegram_last_name', sa.String(length=255), nullable=True),
        sa.Column('telegram_language_code', sa.String(length=10), nullable=True),
        sa.Column('preferred_language', sa.String(length=5), nullable=True, server_default='ru'),
        sa.Column('current_agent_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('last_active_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['current_agent_id'], ['agents.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_chat_id')
    )
    op.create_index('ix_users_telegram_chat_id', 'users', ['telegram_chat_id'], unique=True)

    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('bil24_user_id', sa.BigInteger(), nullable=False),
        sa.Column('bil24_session_id', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('bil24_order_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='NEW'),
        sa.Column('total_sum', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True, server_default='RUB'),
        sa.Column('ticket_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create tickets table
    op.create_table(
        'tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('bil24_ticket_id', sa.BigInteger(), nullable=False),
        sa.Column('event_name', sa.String(length=500), nullable=False),
        sa.Column('event_date', sa.DateTime(), nullable=False),
        sa.Column('venue_name', sa.String(length=500), nullable=False),
        sa.Column('sector', sa.String(length=255), nullable=True),
        sa.Column('row', sa.String(length=50), nullable=True),
        sa.Column('seat', sa.String(length=50), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('qr_code_data', sa.Text(), nullable=True),
        sa.Column('barcode_data', sa.Text(), nullable=True),
        sa.Column('barcode_number', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='VALID'),
        sa.Column('sent_to_user', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create admin_users table
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True, server_default='super_admin'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )

    # Create webhook_logs table
    op.create_table(
        'webhook_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('success', sa.Boolean(), nullable=True, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('key')
    )


def downgrade() -> None:
    """Drop all database tables."""
    op.drop_table('system_settings')
    op.drop_table('webhook_logs')
    op.drop_table('admin_users')
    op.drop_table('tickets')
    op.drop_table('orders')
    op.drop_table('user_sessions')
    op.drop_index('ix_users_telegram_chat_id', table_name='users')
    op.drop_table('users')
    op.drop_index('ix_agents_fid', table_name='agents')
    op.drop_table('agents')
