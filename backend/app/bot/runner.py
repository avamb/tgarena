"""
Telegram Bot Runner

Script to run the bot in polling mode (for development) or webhook mode (for production).
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from aiogram import Bot

try:
    from app.bot.bot import create_bot, dp
    from app.bot.handlers import register_handlers
    from app.core.config import settings
    from app.core.database import init_db, engine
    from app.core.redis_client import ping_redis
except ModuleNotFoundError:
    from backend.app.bot.bot import create_bot, dp
    from backend.app.bot.handlers import register_handlers
    from backend.app.core.config import settings
    from backend.app.core.database import init_db, engine
    from backend.app.core.redis_client import ping_redis

from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def check_infrastructure_health():
    """
    Perform startup health checks on PostgreSQL and Redis.

    Raises SystemExit with a clear error message if services are unavailable.
    """
    # Check PostgreSQL connectivity
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("✓ PostgreSQL health check: OK")
    except Exception as e:
        logger.critical(f"✗ PostgreSQL health check FAILED: {e}")
        raise SystemExit(f"Cannot start bot: PostgreSQL is unavailable - {e}")

    # Check Redis connectivity
    try:
        redis_ok = await ping_redis()
        if redis_ok:
            logger.info("✓ Redis health check: OK")
        else:
            logger.warning("⚠ Redis health check: PING returned False (degraded mode)")
    except Exception as e:
        logger.warning(f"⚠ Redis health check: {e} (bot will run without caching)")


async def on_startup(bot: Bot):
    """Actions to perform on bot startup."""
    # Perform infrastructure health checks
    await check_infrastructure_health()

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Get bot info
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")


async def on_shutdown(bot: Bot):
    """Actions to perform on bot shutdown."""
    logger.info("Bot shutting down...")


async def run_polling():
    """Run bot in polling mode (for development)."""
    logger.info("Starting bot in polling mode...")

    # Create bot instance
    bot = create_bot()

    # Register handlers
    register_handlers(dp)

    # Set up startup/shutdown callbacks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        # Delete webhook in case it was set
        await bot.delete_webhook(drop_pending_updates=True)

        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


async def run_webhook():
    """Run bot in webhook mode (for production)."""
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    logger.info("Starting bot in webhook mode...")

    if not settings.TELEGRAM_WEBHOOK_URL:
        raise ValueError("TELEGRAM_WEBHOOK_URL is not set for webhook mode")

    # Create bot instance
    bot = create_bot()

    # Register handlers
    register_handlers(dp)

    # Set webhook
    await bot.set_webhook(
        url=settings.TELEGRAM_WEBHOOK_URL,
        drop_pending_updates=True
    )

    # Create aiohttp application
    app = web.Application()
    webhook_path = "/webhook/telegram"

    # Configure webhook handler
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_handler.register(app, path=webhook_path)

    # Set up application with dispatcher
    setup_application(app, dp, bot=bot)

    # Run web server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

    logger.info(f"Webhook server started on port 8080")

    # Keep running
    await asyncio.Event().wait()


def main():
    """Main entry point."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set!")
        sys.exit(1)

    # Check if token is placeholder
    if settings.TELEGRAM_BOT_TOKEN.startswith("1234567890:"):
        logger.error(
            "TELEGRAM_BOT_TOKEN appears to be a placeholder. "
            "Please set a real bot token from @BotFather."
        )
        sys.exit(1)

    try:
        # Use polling mode for development, webhook for production
        if settings.ENV == "production" and settings.TELEGRAM_WEBHOOK_URL:
            asyncio.run(run_webhook())
        else:
            asyncio.run(run_polling())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Bot crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
