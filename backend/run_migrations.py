"""
Database migration runner for Docker.

Runs Alembic migrations with proper path setup.
Falls back to SQLAlchemy create_all if Alembic fails.
"""

import os
import sys

# Ensure backend/ is on the path so 'from app.*' imports work
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Also add project root for 'from backend.app.*' imports
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)


def run_alembic():
    """Try running Alembic migrations."""
    from alembic.config import Config
    from alembic import command

    alembic_ini = os.path.join(backend_dir, "alembic.ini")
    if not os.path.exists(alembic_ini):
        print(f"alembic.ini not found at {alembic_ini}")
        return False

    try:
        alembic_cfg = Config(alembic_ini)
        # Override script_location to absolute path
        alembic_cfg.set_main_option(
            "script_location",
            os.path.join(backend_dir, "migrations"),
        )
        # Override sqlalchemy.url from environment
        db_url = os.environ.get("DATABASE_URL", "")
        if db_url:
            # Alembic needs sync driver
            sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

        command.upgrade(alembic_cfg, "head")
        print("Alembic migrations completed successfully")
        return True
    except Exception as e:
        print(f"Alembic migration failed: {e}")
        return False


def run_create_all():
    """Fallback: use SQLAlchemy create_all for missing tables/columns."""
    import asyncio
    from sqlalchemy import text

    # Import after path setup
    from app.core.database import engine, Base
    from app import models  # noqa: F401 — registers models with Base

    async def migrate():
        # Create all tables that don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("SQLAlchemy create_all completed")

            # Add columns that create_all won't add to existing tables
            alter_statements = [
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS payment_type VARCHAR(30) DEFAULT 'bill24_acquiring'",
                "ALTER TABLE agents ALTER COLUMN payment_type TYPE VARCHAR(30)",
                "UPDATE agents SET payment_type = 'bill24_acquiring' WHERE payment_type IS NULL",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS stripe_account_id VARCHAR(255)",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS stripe_account_status VARCHAR(50)",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS stripe_charges_enabled BOOLEAN DEFAULT FALSE",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS stripe_payouts_enabled BOOLEAN DEFAULT FALSE",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS agent_operational_status VARCHAR(20) DEFAULT 'active'",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_type VARCHAR(30) DEFAULT 'bill24_acquiring'",
                "ALTER TABLE orders ALTER COLUMN payment_type TYPE VARCHAR(30)",
                "UPDATE orders SET payment_type = 'bill24_acquiring' WHERE payment_type IS NULL",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_provider VARCHAR(30)",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_url TEXT",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS bil24_form_url TEXT",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS reservation_expires_at TIMESTAMP",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS ticket_amount_minor BIGINT",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS service_fee_amount_minor BIGINT",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS gross_amount_minor BIGINT",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS platform_fee_amount_minor BIGINT",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS stripe_fee_estimated_minor BIGINT",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS stripe_fee_actual_minor BIGINT",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS stripe_session_id VARCHAR(255)",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS stripe_payment_intent_id VARCHAR(255)",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS stripe_charge_id VARCHAR(255)",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS stripe_transfer_id VARCHAR(255)",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS stripe_application_fee_amount_minor BIGINT",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS refund_total_minor BIGINT DEFAULT 0",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS risk_state VARCHAR(30)",
            ]
            for stmt in alter_statements:
                try:
                    await conn.execute(text(stmt))
                except Exception as e:
                    # Column might already exist
                    print(f"  Note: {e}")

            print("Column migrations completed")

    asyncio.run(migrate())


if __name__ == "__main__":
    print(f"Running migrations from {backend_dir}")
    print(f"DATABASE_URL set: {bool(os.environ.get('DATABASE_URL'))}")

    if not run_alembic():
        print("Falling back to create_all + ALTER TABLE...")
        run_create_all()

    print("Migration done.")
