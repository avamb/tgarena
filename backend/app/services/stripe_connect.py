"""Stripe Connect helpers for onboarding, checkout, and refunds."""

import json
import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.core.config import settings
except ModuleNotFoundError:
    from backend.app.core.config import settings

from .money import normalize_currency, to_minor


logger = logging.getLogger(__name__)


def _get_stripe_client():
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe is not configured")

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _get_value(data: Any, key: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def _derive_account_status(account: Any) -> str:
    if _get_value(account, "charges_enabled") and _get_value(account, "payouts_enabled"):
        return "active"
    if _get_value(account, "details_submitted"):
        return "pending_review"
    return "pending_onboarding"


def _apply_account_snapshot(agent: Any, account: Any) -> Any:
    agent.stripe_account_id = _get_value(account, "id")
    agent.stripe_account_status = _derive_account_status(account)
    agent.stripe_charges_enabled = bool(_get_value(account, "charges_enabled"))
    agent.stripe_payouts_enabled = bool(_get_value(account, "payouts_enabled"))
    return agent


async def sync_account_snapshot(agent: Any, account: Any, db: AsyncSession) -> Any:
    """Persist Stripe account capability flags from an already available account object."""
    _apply_account_snapshot(agent=agent, account=account)
    await db.flush()
    return agent


def build_order_amounts(order: Any, fee_minor: int | None = None) -> dict[str, int | str]:
    """Derive Stripe-related order money fields in minor units."""
    currency = normalize_currency(_get_value(order, "currency") or "ILS")
    gross_amount_minor = _get_value(order, "gross_amount_minor")
    if gross_amount_minor is None:
        gross_amount_minor = to_minor(_get_value(order, "total_sum"), currency)

    ticket_amount_minor = _get_value(order, "ticket_amount_minor")
    if ticket_amount_minor is None:
        ticket_amount_minor = gross_amount_minor

    service_fee_amount_minor = _get_value(order, "service_fee_amount_minor")
    if service_fee_amount_minor is None:
        service_fee_amount_minor = max(0, gross_amount_minor - ticket_amount_minor)

    platform_fee_amount_minor = _get_value(order, "platform_fee_amount_minor")
    if platform_fee_amount_minor is None:
        platform_fee_amount_minor = fee_minor
    if platform_fee_amount_minor is None:
        platform_fee_amount_minor = service_fee_amount_minor

    platform_fee_amount_minor = max(0, min(platform_fee_amount_minor, gross_amount_minor))

    return {
        "currency": currency,
        "ticket_amount_minor": ticket_amount_minor,
        "service_fee_amount_minor": service_fee_amount_minor,
        "gross_amount_minor": gross_amount_minor,
        "platform_fee_amount_minor": platform_fee_amount_minor,
    }


async def create_connected_account(agent: Any, db: AsyncSession) -> Any:
    """Create a Stripe Connect account for an agent."""
    if getattr(agent, "stripe_account_id", None):
        return await refresh_account_status(agent=agent, db=db)

    stripe = _get_stripe_client()
    account_payload = {
        "type": "express",
        "metadata": {
            "agent_id": str(agent.id),
        },
    }
    if settings.STRIPE_CONNECT_PLATFORM_COUNTRY:
        account_payload["country"] = settings.STRIPE_CONNECT_PLATFORM_COUNTRY

    account = stripe.Account.create(**account_payload)
    agent.payment_type = "stripe_connect"
    return await sync_account_snapshot(agent=agent, account=account, db=db)


def create_onboarding_link(agent: Any, refresh_url: str, return_url: str) -> Any:
    """Create a Stripe onboarding link for an existing connected account."""
    if not getattr(agent, "stripe_account_id", None):
        raise ValueError("Agent does not have a Stripe account")

    stripe = _get_stripe_client()
    return stripe.AccountLink.create(
        account=agent.stripe_account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )


async def refresh_account_status(agent: Any, db: AsyncSession) -> Any:
    """Refresh Stripe Connect capability flags for an agent."""
    if not getattr(agent, "stripe_account_id", None):
        raise ValueError("Agent does not have a Stripe account")

    stripe = _get_stripe_client()
    account = stripe.Account.retrieve(agent.stripe_account_id)
    return await sync_account_snapshot(agent=agent, account=account, db=db)


def build_destination_charge_payload(order: Any, agent: Any, fee_minor: int | None = None) -> dict[str, Any]:
    """Build a Checkout Session payload for a destination charge."""
    amounts = build_order_amounts(order=order, fee_minor=fee_minor)

    return {
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
        "payment_intent_data": {
            "application_fee_amount": int(amounts["platform_fee_amount_minor"]),
            "transfer_data": {
                "destination": agent.stripe_account_id,
            },
            "metadata": {
                "order_id": str(order.id),
                "agent_id": str(agent.id),
            },
        },
        "metadata": {
            "order_id": str(order.id),
            "agent_id": str(agent.id),
            "bil24_order_id": str(getattr(order, "bil24_order_id", "")),
        },
    }


async def ensure_order_charge_id(order: Any, db: AsyncSession) -> str:
    """Resolve and persist the latest Stripe charge ID for an order."""
    charge_id = getattr(order, "stripe_charge_id", None)
    if charge_id:
        return str(charge_id)

    payment_intent_id = getattr(order, "stripe_payment_intent_id", None)
    if not payment_intent_id:
        raise ValueError("Order does not have a Stripe PaymentIntent ID")

    stripe = _get_stripe_client()
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    charge_id = _get_value(payment_intent, "latest_charge")
    if not charge_id:
        raise ValueError("Stripe PaymentIntent does not have a latest charge")

    order.stripe_charge_id = str(charge_id)
    await db.flush()
    return str(charge_id)


def create_order_refund(
    order: Any,
    amount_minor: int,
    *,
    reason: Optional[str] = None,
    reverse_transfer: bool = True,
    refund_application_fee: bool = False,
) -> Any:
    """Create a Stripe refund for a regular or Connect order."""
    if amount_minor <= 0:
        raise ValueError("amount_minor must be positive")

    charge_id = getattr(order, "stripe_charge_id", None)
    if not charge_id:
        raise ValueError("Order does not have a Stripe charge ID")

    stripe = _get_stripe_client()
    refund_payload: dict[str, Any] = {
        "charge": charge_id,
        "amount": int(amount_minor),
        "metadata": {
            "order_id": str(getattr(order, "id", "")),
            "agent_id": str(getattr(order, "agent_id", "")),
        },
    }

    if reason:
        normalized_reason = reason.strip()
        if normalized_reason in {"duplicate", "fraudulent", "requested_by_customer"}:
            refund_payload["reason"] = normalized_reason
        else:
            refund_payload["metadata"]["internal_reason"] = normalized_reason

    is_connect_order = (
        getattr(order, "payment_type", None) == "stripe_connect"
        or getattr(order, "payment_provider", None) == "stripe_connect"
    )
    if is_connect_order:
        refund_payload["reverse_transfer"] = bool(reverse_transfer)
        if refund_application_fee:
            refund_payload["refund_application_fee"] = True

    return stripe.Refund.create(**refund_payload)


def verify_webhook_signature(payload: bytes | str, sig_header: str | None) -> dict[str, Any]:
    """Validate and deserialize a Stripe webhook event."""
    stripe = _get_stripe_client()

    webhook_secrets = [
        secret
        for secret in (
            settings.STRIPE_WEBHOOK_SECRET,
            settings.STRIPE_CONNECT_WEBHOOK_SECRET,
        )
        if secret
    ]
    if webhook_secrets:
        last_error: Optional[Exception] = None
        for secret in webhook_secrets:
            try:
                event = stripe.Webhook.construct_event(
                    payload=payload,
                    sig_header=sig_header,
                    secret=secret,
                )
                return dict(event)
            except Exception as exc:
                last_error = exc
                logger.info("Stripe webhook signature did not match provided secret")

        if last_error is not None:
            raise last_error

    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    return json.loads(payload)
