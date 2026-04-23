"""Stripe payment endpoints, including Stripe Connect support."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

try:
    from app.core.config import settings
    from app.core.database import async_session_maker
    from app.models import Agent, AgentOperationalStatus, Order, User
    from app.services import (
        apply_refund_outcome,
        build_sale_postings,
        create_refund_case_from_webhook,
        ensure_order_charge_id,
        evaluate_agent_risk,
        get_admin_risk_settings,
        get_wallet_for_agent_currency,
        post_entries,
    )
    from app.services.stripe_connect import (
        build_destination_charge_payload,
        build_order_amounts,
        sync_account_snapshot,
        verify_webhook_signature,
    )
except ModuleNotFoundError:
    from backend.app.core.config import settings
    from backend.app.core.database import async_session_maker
    from backend.app.models import Agent, AgentOperationalStatus, Order, User
    from backend.app.services import (
        apply_refund_outcome,
        build_sale_postings,
        create_refund_case_from_webhook,
        ensure_order_charge_id,
        evaluate_agent_risk,
        get_admin_risk_settings,
        get_wallet_for_agent_currency,
        post_entries,
    )
    from backend.app.services.stripe_connect import (
        build_destination_charge_payload,
        build_order_amounts,
        sync_account_snapshot,
        verify_webhook_signature,
    )

logger = logging.getLogger(__name__)

payments_router = APIRouter()


class CreateSessionRequest(BaseModel):
    order_id: int


class CreateSessionResponse(BaseModel):
    client_secret: str
    publishable_key: str
    order_id: int


def _get_stripe_client():
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _get_value(data: Any, key: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def _utcnow() -> datetime:
    """Return a naive UTC datetime compatible with existing DB columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _raise_stripe_api_error(action: str, exc: Exception) -> None:
    raise HTTPException(status_code=502, detail=f"Stripe {action} failed: {exc}") from exc


def _build_event_source_id(event: Any, event_type: str, event_object: Any) -> str:
    event_id = _get_value(event, "id")
    if event_id:
        return str(event_id)

    object_id = _get_value(event_object, "id")
    payment_intent_id = _get_value(event_object, "payment_intent")
    amount_refunded = _get_value(event_object, "amount_refunded")
    parts = [event_type, object_id, payment_intent_id]
    if amount_refunded is not None:
        parts.append(str(amount_refunded))
    return ":".join(str(part) for part in parts if part)


def _extract_latest_refund_id(charge_object: Any) -> Optional[str]:
    refunds = _get_value(charge_object, "refunds", {}) or {}
    refund_items = _get_value(refunds, "data", []) or []
    if refund_items:
        return _get_value(refund_items[-1], "id")
    return None


async def _run_risk_engine_for_order(order: Order, db) -> Optional[str]:
    wallet = await get_wallet_for_agent_currency(
        agent_id=order.agent_id,
        currency=order.currency,
        db=db,
    )
    if not wallet:
        return None

    agent_result = await db.execute(select(Agent).where(Agent.id == order.agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        return None

    evaluation = await evaluate_agent_risk(agent=agent, wallet=wallet, db=db)
    order.risk_state = evaluation.status
    await db.flush()
    return evaluation.status


async def _apply_sale_postings(order: Order, event: Any, event_type: str, event_object: Any, db) -> None:
    await post_entries(
        postings=build_sale_postings(
            order=order,
            source="stripe_webhook_sale",
            source_id=_build_event_source_id(event=event, event_type=event_type, event_object=event_object),
        ),
        db=db,
        idempotent=True,
    )
    await _run_risk_engine_for_order(order=order, db=db)


async def _get_order_by_id(db, order_id: int) -> Optional[Order]:
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


async def _get_order_by_stripe_reference(
    db,
    order_id: Optional[int] = None,
    session_id: Optional[str] = None,
    payment_intent_id: Optional[str] = None,
    charge_id: Optional[str] = None,
) -> Optional[Order]:
    if order_id is not None:
        return await _get_order_by_id(db=db, order_id=order_id)

    if session_id:
        result = await db.execute(select(Order).where(Order.stripe_session_id == session_id))
        order = result.scalar_one_or_none()
        if order:
            return order

    if payment_intent_id:
        result = await db.execute(
            select(Order).where(Order.stripe_payment_intent_id == payment_intent_id)
        )
        order = result.scalar_one_or_none()
        if order:
            return order

    if charge_id:
        result = await db.execute(select(Order).where(Order.stripe_charge_id == charge_id))
        return result.scalar_one_or_none()

    return None


async def _deliver_paid_order(order: Order, db) -> None:
    user_result = await db.execute(select(User).where(User.id == order.user_id))
    user = user_result.scalar_one_or_none()

    agent_result = await db.execute(select(Agent).where(Agent.id == order.agent_id))
    agent = agent_result.scalar_one_or_none()

    if not user or not agent:
        return

    try:
        try:
            from app.bot.purchase_handlers import _deliver_tickets
        except ModuleNotFoundError:
            from backend.app.bot.purchase_handlers import _deliver_tickets

        asyncio.create_task(
            _deliver_tickets(
                order.id,
                order.bil24_order_id,
                user.telegram_chat_id,
                agent,
                user.preferred_language or "en",
            )
        )
    except Exception as exc:
        logger.error("Ticket delivery failed: %s", exc)


async def _mark_order_paid(order: Order, stripe_object: Any, db) -> str:
    if order.status == "PAID":
        return "already_paid"

    order.status = "PAID"
    order.paid_at = _utcnow()
    order.payment_provider = order.payment_provider or (
        "stripe_connect" if order.payment_type == "stripe_connect" else "stripe"
    )
    order.stripe_session_id = order.stripe_session_id or _get_value(stripe_object, "id")
    order.stripe_payment_intent_id = order.stripe_payment_intent_id or _get_value(
        stripe_object, "payment_intent"
    )
    if order.stripe_payment_intent_id and not getattr(order, "stripe_charge_id", None):
        try:
            await ensure_order_charge_id(order=order, db=db)
        except Exception as exc:
            logger.warning("Unable to resolve Stripe charge for order %s: %s", order.id, exc)
    await db.flush()
    await _deliver_paid_order(order=order, db=db)
    return "paid"


def _build_standard_checkout_payload(order: Order, base_url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    amounts = build_order_amounts(order=order, fee_minor=0)
    payload = {
        "ui_mode": "embedded",
        "payment_method_types": ["card"],
        "line_items": [
            {
                "price_data": {
                    "currency": str(amounts["currency"]).lower(),
                    "product_data": {
                        "name": f"Tickets (Order #{order.id})",
                    },
                    "unit_amount": int(amounts["gross_amount_minor"]),
                },
                "quantity": 1,
            }
        ],
        "mode": "payment",
        "return_url": f"{base_url}/static/pay.html?order_id={order.id}&session_id={{CHECKOUT_SESSION_ID}}",
        "metadata": {
            "order_id": str(order.id),
            "bil24_order_id": str(order.bil24_order_id),
        },
    }
    return payload, amounts


async def _get_checkout_base_url(db) -> str:
    settings_payload = await get_admin_risk_settings(db=db)
    return str(settings_payload["payment_success_url"])


@payments_router.post("/create-session", response_model=CreateSessionResponse)
async def create_checkout_session(request: CreateSessionRequest):
    """Create Stripe Embedded Checkout Session."""
    stripe = _get_stripe_client()

    async with async_session_maker() as db:
        base_url = await _get_checkout_base_url(db=db)
        order = await _get_order_by_id(db=db, order_id=request.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status != "NEW":
            raise HTTPException(status_code=400, detail="Order already processed")

        agent_result = await db.execute(select(Agent).where(Agent.id == order.agent_id))
        agent = agent_result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        if not bool(getattr(agent, "is_active", True)):
            raise HTTPException(status_code=409, detail="Agent is inactive")
        agent_operational_status = str(
            getattr(agent, "agent_operational_status", AgentOperationalStatus.ACTIVE.value)
            or AgentOperationalStatus.ACTIVE.value
        )
        if agent_operational_status in {
            AgentOperationalStatus.RESTRICTED.value,
            AgentOperationalStatus.BLOCKED.value,
            AgentOperationalStatus.FORCE_BLOCKED.value,
        }:
            raise HTTPException(
                status_code=409,
                detail=f"Agent is not allowed to create new checkout sessions ({agent_operational_status})",
            )

        if agent.payment_type == "stripe_connect":
            if not agent.stripe_account_id:
                raise HTTPException(status_code=409, detail="Agent Stripe Connect account is not configured")
            if not agent.stripe_charges_enabled:
                raise HTTPException(status_code=409, detail="Agent Stripe Connect account is not ready to charge")

            payload = build_destination_charge_payload(order=order, agent=agent)
            amounts = build_order_amounts(order=order)
            payload["return_url"] = (
                f"{base_url}/static/pay.html?order_id={order.id}&session_id={{CHECKOUT_SESSION_ID}}"
            )
            order.payment_type = "stripe_connect"
            order.payment_provider = "stripe_connect"
            order.stripe_application_fee_amount_minor = int(amounts["platform_fee_amount_minor"])
        else:
            payload, amounts = _build_standard_checkout_payload(order=order, base_url=base_url)
            order.payment_type = "stripe"
            order.payment_provider = "stripe"
            order.stripe_application_fee_amount_minor = 0

        try:
            session = stripe.checkout.Session.create(**payload)
        except Exception as exc:
            _raise_stripe_api_error("checkout session creation", exc)

        order.ticket_amount_minor = int(amounts["ticket_amount_minor"])
        order.service_fee_amount_minor = int(amounts["service_fee_amount_minor"])
        order.gross_amount_minor = int(amounts["gross_amount_minor"])
        order.platform_fee_amount_minor = int(amounts["platform_fee_amount_minor"])
        order.payment_url = session.id
        order.stripe_session_id = session.id
        order.stripe_payment_intent_id = _get_value(session, "payment_intent")

        await db.commit()

        return CreateSessionResponse(
            client_secret=session.client_secret,
            publishable_key=settings.STRIPE_PUBLISHABLE_KEY or "",
            order_id=order.id,
        )


@payments_router.post("/create-intent", response_model=CreateSessionResponse)
async def create_intent_compat(request: CreateSessionRequest):
    """Alias for create-session (backward compatibility)."""
    return await create_checkout_session(request)


@payments_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe and Stripe Connect webhooks."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = verify_webhook_signature(payload=payload, sig_header=sig_header)
    except Exception as exc:
        logger.warning("Stripe webhook verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc

    event_type = _get_value(event, "type")
    event_object = _get_value(_get_value(event, "data", {}), "object", {})

    async with async_session_maker() as db:
        if event_type == "checkout.session.completed":
            metadata = _get_value(event_object, "metadata", {}) or {}
            order_id = metadata.get("order_id")
            order = await _get_order_by_stripe_reference(
                db=db,
                order_id=int(order_id) if order_id else None,
                session_id=_get_value(event_object, "id"),
                payment_intent_id=_get_value(event_object, "payment_intent"),
            )
            if not order:
                return {"received": True, "event_type": event_type, "result": "order_not_found"}

            order.stripe_session_id = _get_value(event_object, "id") or order.stripe_session_id
            order.stripe_payment_intent_id = (
                _get_value(event_object, "payment_intent") or order.stripe_payment_intent_id
            )
            await _apply_sale_postings(
                order=order,
                event=event,
                event_type=event_type,
                event_object=event_object,
                db=db,
            )
            result = await _mark_order_paid(order=order, stripe_object=event_object, db=db)
            await db.commit()
            return {"received": True, "event_type": event_type, "result": result}

        if event_type == "payment_intent.payment_failed":
            metadata = _get_value(event_object, "metadata", {}) or {}
            order_id = metadata.get("order_id")
            order = await _get_order_by_stripe_reference(
                db=db,
                order_id=int(order_id) if order_id else None,
                payment_intent_id=_get_value(event_object, "id"),
            )
            if order:
                order.risk_state = "payment_failed"
                await db.commit()
            return {"received": True, "event_type": event_type}

        if event_type == "charge.refunded":
            metadata = _get_value(event_object, "metadata", {}) or {}
            order_id = metadata.get("order_id")
            order = await _get_order_by_stripe_reference(
                db=db,
                order_id=int(order_id) if order_id else None,
                payment_intent_id=_get_value(event_object, "payment_intent"),
                charge_id=_get_value(event_object, "id"),
            )
            if order:
                order.stripe_charge_id = _get_value(event_object, "id") or order.stripe_charge_id
                new_refund_total_minor = max(
                    int(order.refund_total_minor or 0),
                    int(_get_value(event_object, "amount_refunded", 0) or 0),
                )
                refund_delta_minor = new_refund_total_minor - int(order.refund_total_minor or 0)
                if refund_delta_minor > 0:
                    refund_case = await create_refund_case_from_webhook(
                        order=order,
                        refund_amount_minor=refund_delta_minor,
                        stripe_refund_id=_extract_latest_refund_id(event_object),
                        reason="stripe charge.refunded webhook",
                        db=db,
                    )
                    await apply_refund_outcome(
                        refund_case=refund_case,
                        db=db,
                        source="stripe_webhook_refund",
                        source_id=_build_event_source_id(
                            event=event,
                            event_type=event_type,
                            event_object=event_object,
                        ),
                    )
                    order.risk_state = getattr(order, "risk_state", None) or "refund_processed"
                order.refund_total_minor = new_refund_total_minor
                if order.gross_amount_minor and order.refund_total_minor >= order.gross_amount_minor:
                    order.status = "REFUNDED"
                await _run_risk_engine_for_order(order=order, db=db)
                await db.commit()
            return {"received": True, "event_type": event_type}

        if event_type == "charge.dispute.created":
            metadata = _get_value(event_object, "metadata", {}) or {}
            order_id = metadata.get("order_id")
            order = await _get_order_by_stripe_reference(
                db=db,
                order_id=int(order_id) if order_id else None,
                payment_intent_id=_get_value(event_object, "payment_intent"),
                charge_id=_get_value(event_object, "charge"),
            )
            if order:
                order.stripe_payment_intent_id = (
                    _get_value(event_object, "payment_intent") or order.stripe_payment_intent_id
                )
                order.stripe_charge_id = _get_value(event_object, "charge") or order.stripe_charge_id
                order.risk_state = "charge_dispute_created"
                await db.commit()
            return {"received": True, "event_type": event_type}

        if event_type == "account.updated":
            account_id = _get_value(event_object, "id")
            if account_id:
                result = await db.execute(select(Agent).where(Agent.stripe_account_id == account_id))
                agent = result.scalar_one_or_none()
                if agent:
                    await sync_account_snapshot(agent=agent, account=event_object, db=db)
                    await db.commit()
            return {"received": True, "event_type": event_type}

        return {"received": True, "event_type": event_type, "ignored": True}


@payments_router.get("/verify")
async def verify_payment(session_id: str, order_id: int):
    """Verify Stripe payment and trigger ticket delivery."""
    stripe = _get_stripe_client()

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        logger.error("Stripe session retrieve error: %s", exc)
        _raise_stripe_api_error("session retrieval", exc)

    if _get_value(session, "status") != "complete":
        return {"status": "pending", "order_id": order_id}

    async with async_session_maker() as db:
        order = await _get_order_by_id(db=db, order_id=order_id)
        if not order:
            return {"status": "not_found", "order_id": order_id}

        order.stripe_session_id = _get_value(session, "id") or order.stripe_session_id
        order.stripe_payment_intent_id = _get_value(session, "payment_intent") or order.stripe_payment_intent_id
        status = await _mark_order_paid(order=order, stripe_object=session, db=db)
        await db.commit()

    logger.info("Stripe payment verified: order=%s, session=%s", order_id, session_id)
    return {"status": status, "order_id": order_id}


@payments_router.get("/success")
async def payment_success(order_id: int, session_id: str = ""):
    """Redirect endpoint for non-embedded checkout (fallback)."""
    bot_username = settings.TELEGRAM_BOT_USERNAME or "ArenaAppTestZone_bot"
    if session_id:
        await verify_payment(session_id, order_id)
    return RedirectResponse(url=f"https://t.me/{bot_username}?start=paid")
