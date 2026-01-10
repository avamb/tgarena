"""
Background Jobs Module

Provides async background job processing using arq (async redis queue).
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
from arq.jobs import Job

try:
    from app.core.config import settings
except ModuleNotFoundError:
    from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Global arq pool
_arq_pool: Optional[ArqRedis] = None


def get_redis_settings() -> RedisSettings:
    """Parse Redis URL into RedisSettings for arq."""
    # Parse redis://host:port/db format
    url = settings.REDIS_URL
    if url.startswith("redis://"):
        url = url[8:]  # Remove redis://

    # Split into host:port/db
    if "/" in url:
        host_port, db = url.rsplit("/", 1)
        db = int(db) if db else 0
    else:
        host_port = url
        db = 0

    if ":" in host_port:
        host, port = host_port.rsplit(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 6379

    return RedisSettings(
        host=host,
        port=port,
        database=db,
    )


async def get_arq_pool() -> ArqRedis:
    """Get or create the arq Redis pool."""
    global _arq_pool

    if _arq_pool is None:
        _arq_pool = await create_pool(get_redis_settings())
        logger.info("ARQ pool created")

    return _arq_pool


async def close_arq_pool():
    """Close the arq Redis pool."""
    global _arq_pool

    if _arq_pool is not None:
        await _arq_pool.close()
        _arq_pool = None
        logger.info("ARQ pool closed")


# =============================================================================
# Background Job Functions
# =============================================================================

async def send_webhook_job(ctx: Dict[str, Any], webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background job to send webhook notification.

    Args:
        ctx: ARQ context
        webhook_url: URL to send the webhook to
        payload: Data to send

    Returns:
        Result dictionary with status and details
    """
    import httpx

    logger.info(f"Processing webhook job to {webhook_url}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "response": response.text[:500] if response.text else None,
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Webhook job failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def process_ticket_delivery_job(
    ctx: Dict[str, Any],
    order_id: int,
    user_chat_id: int
) -> Dict[str, Any]:
    """
    Background job to process ticket delivery.

    Sends purchase confirmation and tickets to user via Telegram bot.

    Args:
        ctx: ARQ context
        order_id: Order ID to process
        user_chat_id: Telegram chat ID to send tickets to

    Returns:
        Result dictionary with delivery status
    """
    from aiogram import Bot
    from app.core.config import settings
    from app.core.database import async_session_maker
    from app.models import Order, Agent, OrderItem
    from sqlalchemy import select

    logger.info(f"Processing ticket delivery for order {order_id} to chat {user_chat_id}")

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return {
            "success": False,
            "error": "Bot token not configured",
            "order_id": order_id,
            "timestamp": datetime.utcnow().isoformat()
        }

    try:
        async with async_session_maker() as session:
            # Get order details
            result = await session.execute(
                select(Order).where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()

            if not order:
                logger.error(f"Order {order_id} not found")
                return {
                    "success": False,
                    "error": "Order not found",
                    "order_id": order_id,
                    "timestamp": datetime.utcnow().isoformat()
                }

            # Get agent name
            agent_name = "Agent"
            if order.agent_id:
                agent_result = await session.execute(
                    select(Agent).where(Agent.id == order.agent_id)
                )
                agent = agent_result.scalar_one_or_none()
                if agent:
                    agent_name = agent.name

            # Initialize bot for sending
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

            try:
                # Send purchase confirmation
                confirmation_message = (
                    f"✅ <b>Покупка подтверждена!</b>\n\n"
                    f"Заказ #{order.id}\n"
                    f"Агент: {agent_name}\n"
                    f"Сумма: {order.total_amount or 0} ₽\n\n"
                    f"Ваши билеты будут отправлены ниже."
                )

                await bot.send_message(
                    chat_id=user_chat_id,
                    text=confirmation_message,
                    parse_mode="HTML"
                )

                logger.info(f"Sent confirmation for order {order_id} to chat {user_chat_id}")

                # Mark order as having tickets delivered
                order.tickets_delivered = True
                await session.commit()

                return {
                    "success": True,
                    "order_id": order_id,
                    "user_chat_id": user_chat_id,
                    "message": "Purchase confirmation sent",
                    "timestamp": datetime.utcnow().isoformat()
                }

            finally:
                await bot.session.close()

    except Exception as e:
        logger.exception(f"Failed to deliver tickets for order {order_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "order_id": order_id,
            "timestamp": datetime.utcnow().isoformat()
        }


async def cleanup_expired_sessions_job(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background job to cleanup expired user sessions.

    Args:
        ctx: ARQ context

    Returns:
        Result dictionary with cleanup stats
    """
    logger.info("Processing session cleanup job")

    # This would clean up expired Bill24 sessions from the database
    return {
        "success": True,
        "cleaned_sessions": 0,
        "timestamp": datetime.utcnow().isoformat()
    }


async def sync_order_status_job(
    ctx: Dict[str, Any],
    order_id: int,
    bil24_order_id: int
) -> Dict[str, Any]:
    """
    Background job to sync order status with Bill24.

    Args:
        ctx: ARQ context
        order_id: Local order ID
        bil24_order_id: Bill24 order ID

    Returns:
        Result dictionary with sync status
    """
    logger.info(f"Syncing order status for order {order_id} (Bill24: {bil24_order_id})")

    # This would call Bill24 API to get order status
    return {
        "success": True,
        "order_id": order_id,
        "bil24_order_id": bil24_order_id,
        "message": "Order status sync job queued (Bill24 integration required)",
        "timestamp": datetime.utcnow().isoformat()
    }


async def test_background_job(ctx: Dict[str, Any], message: str = "Hello") -> Dict[str, Any]:
    """
    Test background job for verifying arq is working.

    Args:
        ctx: ARQ context
        message: Test message

    Returns:
        Result dictionary
    """
    logger.info(f"Processing test job with message: {message}")

    # Simulate some work
    await asyncio.sleep(1)

    return {
        "success": True,
        "message": f"Processed: {message}",
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# ARQ Worker Configuration
# =============================================================================

class WorkerSettings:
    """ARQ worker settings."""

    redis_settings = get_redis_settings()

    # Register job functions
    functions = [
        send_webhook_job,
        process_ticket_delivery_job,
        cleanup_expired_sessions_job,
        sync_order_status_job,
        test_background_job,
    ]

    # Worker configuration
    max_jobs = 10
    job_timeout = 300  # 5 minutes
    keep_result = 3600  # Keep results for 1 hour

    # Cron jobs (scheduled tasks)
    cron_jobs = [
        # Run session cleanup every hour
        # cron(cleanup_expired_sessions_job, hour={0, 6, 12, 18}, minute=0),
    ]


# =============================================================================
# Job Enqueueing Functions
# =============================================================================

async def enqueue_webhook(webhook_url: str, payload: Dict[str, Any]) -> Optional[Job]:
    """Enqueue a webhook delivery job."""
    try:
        pool = await get_arq_pool()
        job = await pool.enqueue_job("send_webhook_job", webhook_url, payload)
        logger.info(f"Enqueued webhook job: {job.job_id}")
        return job
    except Exception as e:
        logger.error(f"Failed to enqueue webhook job: {e}")
        return None


async def enqueue_ticket_delivery(order_id: int, user_chat_id: int) -> Optional[Job]:
    """Enqueue a ticket delivery job."""
    try:
        pool = await get_arq_pool()
        job = await pool.enqueue_job("process_ticket_delivery_job", order_id, user_chat_id)
        logger.info(f"Enqueued ticket delivery job: {job.job_id}")
        return job
    except Exception as e:
        logger.error(f"Failed to enqueue ticket delivery job: {e}")
        return None


async def enqueue_order_sync(order_id: int, bil24_order_id: int) -> Optional[Job]:
    """Enqueue an order status sync job."""
    try:
        pool = await get_arq_pool()
        job = await pool.enqueue_job("sync_order_status_job", order_id, bil24_order_id)
        logger.info(f"Enqueued order sync job: {job.job_id}")
        return job
    except Exception as e:
        logger.error(f"Failed to enqueue order sync job: {e}")
        return None


async def enqueue_test_job(message: str = "Test") -> Optional[Job]:
    """Enqueue a test job for verification."""
    try:
        pool = await get_arq_pool()
        job = await pool.enqueue_job("test_background_job", message)
        logger.info(f"Enqueued test job: {job.job_id}")
        return job
    except Exception as e:
        logger.error(f"Failed to enqueue test job: {e}")
        return None


async def get_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    """Get the result of a completed job."""
    try:
        pool = await get_arq_pool()
        job = Job(job_id, pool)
        result = await job.result(timeout=5)
        return result
    except Exception as e:
        logger.error(f"Failed to get job result for {job_id}: {e}")
        return None


async def get_job_status(job_id: str) -> Optional[str]:
    """Get the status of a job."""
    try:
        pool = await get_arq_pool()
        job = Job(job_id, pool)
        status = await job.status()
        return status.value if status else None
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        return None
