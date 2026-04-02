"""
Stripe Payment API Endpoints

Creates Checkout Session and handles payment confirmation.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
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


class CreatePaymentRequest(BaseModel):
    order_id: int


class CreatePaymentResponse(BaseModel):
    checkout_url: str
    order_id: int


@payments_router.post("/create-intent", response_model=CreatePaymentResponse)
async def create_checkout_session(request: CreatePaymentRequest):
    """Create Stripe Checkout Session for an order."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    base_url = settings.PAYMENT_SUCCESS_URL or "https://tgtest.arenasoldout.com"
    bot_username = settings.TELEGRAM_BOT_USERNAME or "ArenaAppTestZone_bot"

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
                success_url=f"{base_url}/api/payments/success?order_id={order.id}&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"https://t.me/{bot_username}",
                metadata={
                    "order_id": str(order.id),
                    "bil24_order_id": str(order.bil24_order_id),
                },
                # Pre-fill email to skip email field
                customer_email=f"user_{order.user_id}@ticket.bot",
            )

            order.payment_url = session.id
            order.payment_type = "stripe"
            await db.commit()

            return CreatePaymentResponse(
                checkout_url=session.url,
                order_id=order.id,
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise HTTPException(status_code=500, detail="Payment creation failed")


@payments_router.get("/success")
async def payment_success(order_id: int, session_id: str):
    """
    Stripe redirects here after successful payment.
    Verify payment, update order, trigger ticket delivery, redirect to bot.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    bot_username = settings.TELEGRAM_BOT_USERNAME or "ArenaAppTestZone_bot"

    # Verify with Stripe
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe session retrieve error: {e}")
        return RedirectResponse(url=f"https://t.me/{bot_username}?start=paid")

    if session.payment_status != "paid":
        logger.warning(f"Payment not completed: {session.payment_status}")
        return RedirectResponse(url=f"https://t.me/{bot_username}?start=paid")

    # Update order
    async with async_session_maker() as db:
        result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if order and order.status != "PAID":
            from datetime import datetime
            order.status = "PAID"
            order.paid_at = datetime.utcnow()
            await db.commit()

            # Get user and agent for ticket delivery
            user_result = await db.execute(
                select(User).where(User.id == order.user_id)
            )
            user = user_result.scalar_one_or_none()

            agent_result = await db.execute(
                select(Agent).where(Agent.id == order.agent_id)
            )
            agent = agent_result.scalar_one_or_none()

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
                    logger.error(f"Ticket delivery trigger failed: {e}")

            logger.info(f"Stripe payment confirmed: order={order.id}, session={session_id}")

    # Redirect to bot
    return RedirectResponse(url=f"https://t.me/{bot_username}?start=paid")


@payments_router.post("/confirm")
async def confirm_payment(request: Request):
    """Legacy confirm endpoint — kept for compatibility."""
    body = await request.json()
    order_id = body.get("order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="order_id required")

    async with async_session_maker() as db:
        result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if order and order.status == "PAID":
            return {"status": "paid", "order_id": order.id}

    return {"status": "pending", "order_id": order_id}
