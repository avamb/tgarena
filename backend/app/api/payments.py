"""
Stripe Payment API Endpoints

Creates PaymentIntent and handles payment confirmation for Telegram Mini App.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
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
    order_id: int  # Our DB order ID


class CreatePaymentResponse(BaseModel):
    client_secret: str
    amount: int  # In smallest currency unit (cents/agorot)
    currency: str
    order_id: int
    publishable_key: str


class PaymentConfirmRequest(BaseModel):
    order_id: int
    payment_intent_id: str


@payments_router.post("/create-intent", response_model=CreatePaymentResponse)
async def create_payment_intent(request: CreatePaymentRequest):
    """Create Stripe PaymentIntent for an order."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    async with async_session_maker() as db:
        result = await db.execute(
            select(Order).where(Order.id == request.order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status != "NEW":
            raise HTTPException(status_code=400, detail="Order already processed")

        # Convert to smallest currency unit (cents/agorot)
        amount = int(order.total_sum * 100)
        currency = order.currency.lower() if order.currency else "ils"

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                metadata={
                    "order_id": str(order.id),
                    "bil24_order_id": str(order.bil24_order_id),
                    "telegram_chat_id": str(order.user_id),
                },
                automatic_payment_methods={"enabled": True},
            )

            # Save Stripe payment intent ID to order
            order.payment_url = intent.id
            order.payment_type = "stripe"
            await db.commit()

            return CreatePaymentResponse(
                client_secret=intent.client_secret,
                amount=amount,
                currency=currency,
                order_id=order.id,
                publishable_key=settings.STRIPE_PUBLISHABLE_KEY or "",
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise HTTPException(status_code=500, detail="Payment creation failed")


@payments_router.post("/confirm")
async def confirm_payment(request: PaymentConfirmRequest):
    """
    Confirm payment was successful (called by Mini App after Stripe confirms).

    Verifies with Stripe that the PaymentIntent is actually paid,
    updates order status, and triggers ticket delivery.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Verify with Stripe
    try:
        intent = stripe.PaymentIntent.retrieve(request.payment_intent_id)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe retrieve error: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify payment")

    if intent.status != "succeeded":
        raise HTTPException(
            status_code=400,
            detail=f"Payment not succeeded: {intent.status}",
        )

    # Update order in DB
    async with async_session_maker() as db:
        result = await db.execute(
            select(Order).where(Order.id == request.order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status == "PAID":
            return {"status": "already_paid", "order_id": order.id}

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

    # Trigger ticket delivery
    if user and agent:
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

    logger.info(
        f"Stripe payment confirmed: order={order.id}, "
        f"intent={request.payment_intent_id}"
    )

    return {"status": "paid", "order_id": order.id}
