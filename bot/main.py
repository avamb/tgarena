"""
TG-Ticket-Agent Bot Entry Point

Starts the aiogram bot with polling or webhook mode.
"""

import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    """Set bot commands for menu."""
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="events", description="Browse events"),
        BotCommand(command="mytickets", description="View my tickets"),
        BotCommand(command="help", description="Get help"),
        BotCommand(command="language", description="Change language"),
    ]
    await bot.set_my_commands(commands)


async def check_infrastructure_health():
    """
    Perform startup health checks on PostgreSQL and Redis.

    Checks PostgreSQL (SELECT 1) and Redis (PING) before starting polling.
    Logs status and fails with a clear error if critical services are unavailable.
    """
    database_url = getenv("DATABASE_URL", "")
    redis_url = getenv("REDIS_URL", "redis://localhost:6379/0")

    # Check PostgreSQL connectivity
    if database_url:
        async_url = database_url
        if async_url.startswith("postgresql://"):
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        try:
            engine = create_async_engine(async_url, pool_pre_ping=True)
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()
            await engine.dispose()
            logger.info("✓ PostgreSQL health check: OK")
        except Exception as e:
            logger.critical(f"✗ PostgreSQL health check FAILED: {e}")
            raise SystemExit(f"Cannot start bot: PostgreSQL is unavailable - {e}")
    else:
        logger.warning("⚠ DATABASE_URL not set - skipping PostgreSQL health check")

    # Check Redis connectivity
    try:
        redis_client = await redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        redis_ok = await redis_client.ping()
        await redis_client.aclose()
        if redis_ok:
            logger.info("✓ Redis health check: OK")
        else:
            logger.warning("⚠ Redis health check: PING returned False (degraded mode)")
    except Exception as e:
        logger.warning(f"⚠ Redis health check: {e} (bot will run without caching)")


async def main():
    """Main function to start the bot."""
    # Get token from environment
    token = getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    # Perform infrastructure health checks before starting
    await check_infrastructure_health()

    # Create bot instance
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Create dispatcher
    dp = Dispatcher()

    # Register handlers
    from bot.handlers import register_handlers

    register_handlers(dp)

    # Register middlewares (includes global error handling)
    from bot.middlewares import register_middlewares

    register_middlewares(dp)

    # Set commands
    await set_commands(bot)

    logger.info("Starting bot...")

    # Start polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
