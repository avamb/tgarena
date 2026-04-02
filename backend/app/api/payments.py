"""
Stripe Payment API Endpoints

Stripe Embedded Checkout inside Telegram Mini App.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

try:
    from app.core.config import settings
    from app.core.database import async_session_maker
    from app.models import Order, User, Agent
except ModuleNotFoundError:
    from backend.app.core.config import settings
    from backend.app.core.database import async_session_maker
    from backend.app.models import Order, User, Agent

logger = logging.getLogger(__name__)

payments_router = APIRouter()


class CreateSessionRequest(BaseModel):
    order_id: int


class CreateSessionResponse(BaseModel):
    client_secret: str
    publishable_key: str
    order_id: int


@payments_router.post("/create-session", response_model=CreateSessionResponse)
async def create_checkout_session(request: CreateSessionRequest):
    """Create Stripe Embedded Checkout Session."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    base_url = settings.PAYMENT_SUCCESS_URL or "https://tgtest.arenasoldout.com"

    async with async_session_maker() as db:
        result = await db.execute(
            select(Order).where(Order.id == request.order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status != "NEW":
            raise HTTPException(status_code=400, detail="Order already processed")

        amount = int(order.total_sum * 100)
        currency = order.currency.lower() if order.currency else "ils"

        try:
            session = stripe.checkout.Session.create(
                ui_mode="embedded_page",
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": f"Tickets (Order #{order.id})",
                        },
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                return_url=f"{base_url}/static/pay.html?order_id={order.id}&session_id={{CHECKOUT_SESSION_ID}}",
                metadata={
                    "order_id": str(order.id),
                    "bil24_order_id": str(order.bil24_order_id),
                },
            )

            order.payment_url = session.id
            order.payment_type = "stripe"
            await db.commit()

            return CreateSessionResponse(
                client_secret=session.client_secret,
                publishable_key=settings.STRIPE_PUBLISHABLE_KEY or "",
                order_id=order.id,
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise HTTPException(status_code=500, detail=f"Payment creation failed: {str(e)}")


# Keep old endpoint name for compatibility with pay.html
@payments_router.post("/create-intent", response_model=CreateSessionResponse)
async def create_intent_compat(request: CreateSessionRequest):
    """Alias for create-session (backward compatibility)."""
    return await create_checkout_session(request)


@payments_router.get("/verify")
async def verify_payment(session_id: str, order_id: int):
    """Verify Stripe payment and trigger ticket delivery."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe session retrieve error: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify payment")

    if session.status != "complete":
        return {"status": "pending", "order_id": order_id}

    # Update order
    async with async_session_maker() as db:
        result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return {"status": "not_found", "order_id": order_id}

        if order.status == "PAID":
            return {"status": "already_paid", "order_id": order_id}

        from datetime import datetime
        order.status = "PAID"
        order.paid_at = datetime.utcnow()
        await db.commit()

        # Get user and agent
        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()

        agent_result = await db.execute(select(Agent).where(Agent.id == order.agent_id))
        agent = agent_result.scalar_one_or_none()

    # Trigger ticket delivery
    if user and agent:
        try:
            try:
                from app.bot.purchase_handlers import _deliver_tickets
            except ModuleNotFoundError:
                from backend.app.bot.purchase_handlers import _deliver_tickets

            import asyncio
            asyncio.create_task(
                _deliver_tickets(
                    order.id, order.bil24_order_id,
                    user.telegram_chat_id, agent, "en",
                )
            )
        except Exception as e:
            logger.error(f"Ticket delivery failed: {e}")

    logger.info(f"Stripe payment verified: order={order_id}, session={session_id}")
    return {"status": "paid", "order_id": order_id}


@payments_router.get("/success")
async def payment_success(order_id: int, session_id: str = ""):
    """Redirect endpoint for non-embedded checkout (fallback)."""
    bot_username = settings.TELEGRAM_BOT_USERNAME or "ArenaAppTestZone_bot"
    if session_id:
        # Verify and deliver
        await verify_payment(session_id, order_id)
    return RedirectResponse(url=f"https://t.me/{bot_username}?start=paid")
