"""Tests for Stripe webhook processing."""

import os
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class DummyRequest:
    def __init__(self, payload: bytes, headers=None):
        self._payload = payload
        self.headers = headers or {}

    async def body(self):
        return self._payload


class DummySessionContext:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def test_verify_webhook_signature_accepts_connected_account_secret_fallback():
    from app.services.stripe_connect import verify_webhook_signature

    stripe_client = SimpleNamespace(Webhook=SimpleNamespace())

    def construct_event(payload, sig_header, secret):
        if secret == "whsec_platform":
            raise ValueError("bad signature")
        if secret == "whsec_connected":
            return {"id": "evt_connected", "type": "account.updated"}
        raise AssertionError(f"Unexpected secret {secret}")

    stripe_client.Webhook.construct_event = MagicMock(side_effect=construct_event)

    with patch("app.services.stripe_connect._get_stripe_client", return_value=stripe_client):
        with patch("app.services.stripe_connect.settings.STRIPE_WEBHOOK_SECRET", "whsec_platform"):
            with patch("app.services.stripe_connect.settings.STRIPE_CONNECT_WEBHOOK_SECRET", "whsec_connected"):
                event = verify_webhook_signature(payload=b"{}", sig_header="sig")

    assert event["id"] == "evt_connected"
    assert stripe_client.Webhook.construct_event.call_count == 2


@pytest.mark.asyncio
async def test_checkout_session_completed_marks_order_paid():
    from app.api.payments import stripe_webhook

    order = SimpleNamespace(
        id=123,
        status="NEW",
        paid_at=None,
        payment_type="stripe_connect",
        payment_provider=None,
        stripe_session_id=None,
        stripe_payment_intent_id=None,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order)]
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_123",
                "payment_intent": "pi_123",
                "metadata": {"order_id": "123"},
            }
        },
    }

    with patch("app.api.payments.async_session_maker", return_value=DummySessionContext(db)):
        with patch("app.api.payments.verify_webhook_signature", return_value=event):
            with patch("app.api.payments._apply_sale_postings", new_callable=AsyncMock) as mock_sale_postings:
                with patch("app.api.payments._deliver_paid_order", new_callable=AsyncMock) as mock_delivery:
                    response = await stripe_webhook(DummyRequest(b"{}", {"stripe-signature": "sig"}))

    assert response["result"] == "paid"
    assert order.status == "PAID"
    assert order.stripe_session_id == "cs_123"
    assert order.stripe_payment_intent_id == "pi_123"
    mock_sale_postings.assert_awaited_once()
    mock_delivery.assert_awaited_once()


@pytest.mark.asyncio
async def test_checkout_session_completed_duplicate_event_returns_already_paid_without_delivery():
    from app.api.payments import stripe_webhook

    order = SimpleNamespace(
        id=123,
        status="PAID",
        paid_at=None,
        payment_type="stripe_connect",
        payment_provider="stripe_connect",
        stripe_session_id="cs_existing",
        stripe_payment_intent_id="pi_existing",
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order)]
    db.commit = AsyncMock()

    event = {
        "id": "evt_checkout_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_existing",
                "payment_intent": "pi_existing",
                "metadata": {"order_id": "123"},
            }
        },
    }

    with patch("app.api.payments.async_session_maker", return_value=DummySessionContext(db)):
        with patch("app.api.payments.verify_webhook_signature", return_value=event):
            with patch("app.api.payments._apply_sale_postings", new_callable=AsyncMock) as mock_sale_postings:
                with patch("app.api.payments._deliver_paid_order", new_callable=AsyncMock) as mock_delivery:
                    response = await stripe_webhook(DummyRequest(b"{}", {"stripe-signature": "sig"}))

    assert response["result"] == "already_paid"
    mock_sale_postings.assert_awaited_once()
    mock_delivery.assert_not_awaited()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_account_updated_applies_snapshot_from_event_payload():
    from app.api.payments import stripe_webhook

    agent = SimpleNamespace(
        id=77,
        stripe_account_id="acct_123",
        stripe_account_status="pending_onboarding",
        stripe_charges_enabled=False,
        stripe_payouts_enabled=False,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(agent)]
    db.commit = AsyncMock()

    event = {
        "type": "account.updated",
        "data": {
            "object": {
                "id": "acct_123",
                "details_submitted": True,
                "charges_enabled": True,
                "payouts_enabled": True,
            }
        },
    }

    with patch("app.api.payments.async_session_maker", return_value=DummySessionContext(db)):
        with patch("app.api.payments.verify_webhook_signature", return_value=event):
            with patch("app.api.payments.sync_account_snapshot", new_callable=AsyncMock) as mock_sync:
                response = await stripe_webhook(DummyRequest(b"{}", {"stripe-signature": "sig"}))

    assert response["event_type"] == "account.updated"
    mock_sync.assert_awaited_once_with(agent=agent, account=event["data"]["object"], db=db)


@pytest.mark.asyncio
async def test_payment_intent_payment_failed_marks_order_risk_state():
    from app.api.payments import stripe_webhook

    order = SimpleNamespace(
        id=123,
        risk_state=None,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order)]
    db.commit = AsyncMock()

    event = {
        "type": "payment_intent.payment_failed",
        "data": {
            "object": {
                "id": "pi_123",
                "metadata": {"order_id": "123"},
            }
        },
    }

    with patch("app.api.payments.async_session_maker", return_value=DummySessionContext(db)):
        with patch("app.api.payments.verify_webhook_signature", return_value=event):
            response = await stripe_webhook(DummyRequest(b"{}", {"stripe-signature": "sig"}))

    assert response["event_type"] == "payment_intent.payment_failed"
    assert order.risk_state == "payment_failed"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_charge_refunded_runs_refund_flow_and_updates_order_totals():
    from app.api.payments import stripe_webhook

    order = SimpleNamespace(
        id=123,
        agent_id=77,
        currency="USD",
        status="PAID",
        refund_total_minor=2000,
        gross_amount_minor=10000,
        stripe_charge_id=None,
        risk_state=None,
    )
    refund_case = SimpleNamespace(id=901)

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order)]
    db.commit = AsyncMock()

    event = {
        "id": "evt_refund_1",
        "type": "charge.refunded",
        "data": {
            "object": {
                "id": "ch_123",
                "payment_intent": "pi_123",
                "amount_refunded": 5000,
                "metadata": {"order_id": "123"},
                "refunds": {"data": [{"id": "re_123"}]},
            }
        },
    }

    with patch("app.api.payments.async_session_maker", return_value=DummySessionContext(db)):
        with patch("app.api.payments.verify_webhook_signature", return_value=event):
            with patch(
                "app.api.payments.create_refund_case_from_webhook",
                new_callable=AsyncMock,
                return_value=refund_case,
            ) as mock_create_refund_case:
                with patch("app.api.payments.apply_refund_outcome", new_callable=AsyncMock) as mock_apply_refund:
                    with patch("app.api.payments._run_risk_engine_for_order", new_callable=AsyncMock) as mock_risk:
                        response = await stripe_webhook(DummyRequest(b"{}", {"stripe-signature": "sig"}))

    assert response["event_type"] == "charge.refunded"
    assert order.stripe_charge_id == "ch_123"
    assert order.refund_total_minor == 5000
    mock_create_refund_case.assert_awaited_once()
    mock_apply_refund.assert_awaited_once_with(
        refund_case=refund_case,
        db=db,
        source="stripe_webhook_refund",
        source_id="evt_refund_1",
    )
    mock_risk.assert_awaited_once_with(order=order, db=db)


@pytest.mark.asyncio
async def test_charge_refunded_duplicate_event_skips_duplicate_refund_flow():
    from app.api.payments import stripe_webhook

    order = SimpleNamespace(
        id=123,
        agent_id=77,
        currency="USD",
        status="PAID",
        refund_total_minor=5000,
        gross_amount_minor=10000,
        stripe_charge_id="ch_existing",
        risk_state=None,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order)]
    db.commit = AsyncMock()

    event = {
        "id": "evt_refund_1",
        "type": "charge.refunded",
        "data": {
            "object": {
                "id": "ch_existing",
                "payment_intent": "pi_123",
                "amount_refunded": 5000,
                "metadata": {"order_id": "123"},
                "refunds": {"data": [{"id": "re_123"}]},
            }
        },
    }

    with patch("app.api.payments.async_session_maker", return_value=DummySessionContext(db)):
        with patch("app.api.payments.verify_webhook_signature", return_value=event):
            with patch("app.api.payments.create_refund_case_from_webhook", new_callable=AsyncMock) as mock_create_refund_case:
                with patch("app.api.payments.apply_refund_outcome", new_callable=AsyncMock) as mock_apply_refund:
                    with patch("app.api.payments._run_risk_engine_for_order", new_callable=AsyncMock) as mock_risk:
                        response = await stripe_webhook(DummyRequest(b"{}", {"stripe-signature": "sig"}))

    assert response["event_type"] == "charge.refunded"
    assert order.refund_total_minor == 5000
    mock_create_refund_case.assert_not_awaited()
    mock_apply_refund.assert_not_awaited()
    mock_risk.assert_awaited_once_with(order=order, db=db)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_charge_dispute_created_marks_order_risk_state():
    from app.api.payments import stripe_webhook

    order = SimpleNamespace(
        id=123,
        stripe_charge_id=None,
        stripe_payment_intent_id=None,
        risk_state=None,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order)]
    db.commit = AsyncMock()

    event = {
        "type": "charge.dispute.created",
        "data": {
            "object": {
                "charge": "ch_123",
                "payment_intent": "pi_123",
                "metadata": {"order_id": "123"},
            }
        },
    }

    with patch("app.api.payments.async_session_maker", return_value=DummySessionContext(db)):
        with patch("app.api.payments.verify_webhook_signature", return_value=event):
            response = await stripe_webhook(DummyRequest(b"{}", {"stripe-signature": "sig"}))

    assert response["event_type"] == "charge.dispute.created"
    assert order.stripe_charge_id == "ch_123"
    assert order.stripe_payment_intent_id == "pi_123"
    assert order.risk_state == "charge_dispute_created"
    db.commit.assert_awaited_once()
