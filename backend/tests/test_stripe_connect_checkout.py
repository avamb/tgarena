"""Tests for Stripe Connect checkout session creation."""

from decimal import Decimal
import os
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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


@pytest.mark.asyncio
async def test_create_checkout_session_builds_destination_charge():
    from app.api.payments import CreateSessionRequest, create_checkout_session

    order = SimpleNamespace(
        id=123,
        status="NEW",
        total_sum=Decimal("12.50"),
        currency="USD",
        agent_id=77,
        bil24_order_id=555,
        ticket_amount_minor=1000,
        service_fee_amount_minor=250,
        gross_amount_minor=1250,
        platform_fee_amount_minor=None,
        payment_type="bill24_acquiring",
        payment_provider=None,
        payment_url=None,
        stripe_session_id=None,
        stripe_payment_intent_id=None,
        stripe_application_fee_amount_minor=None,
    )
    agent = SimpleNamespace(
        id=77,
        payment_type="stripe_connect",
        stripe_account_id="acct_123",
        stripe_charges_enabled=True,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order), _scalar_result(agent)]
    db.commit = AsyncMock()

    stripe_session = SimpleNamespace(
        id="cs_123",
        client_secret="secret_123",
        payment_intent="pi_123",
    )
    stripe_client = MagicMock()
    stripe_client.checkout.Session.create.return_value = stripe_session

    with patch("app.api.payments.async_session_maker", return_value=DummySessionContext(db)):
        with patch("app.api.payments._get_stripe_client", return_value=stripe_client):
            with patch(
                "app.api.payments.get_admin_risk_settings",
                new_callable=AsyncMock,
                return_value={"payment_success_url": "https://example.com"},
            ):
                response = await create_checkout_session(CreateSessionRequest(order_id=123))

    create_kwargs = stripe_client.checkout.Session.create.call_args.kwargs
    assert create_kwargs["ui_mode"] == "embedded"
    assert create_kwargs["payment_intent_data"]["transfer_data"]["destination"] == "acct_123"
    assert create_kwargs["payment_intent_data"]["application_fee_amount"] == 250
    assert order.payment_type == "stripe_connect"
    assert order.payment_provider == "stripe_connect"
    assert response.client_secret == "secret_123"


@pytest.mark.asyncio
async def test_create_checkout_session_returns_502_when_stripe_create_fails():
    from app.api.payments import CreateSessionRequest, create_checkout_session

    order = SimpleNamespace(
        id=123,
        status="NEW",
        total_sum=Decimal("12.50"),
        currency="USD",
        agent_id=77,
        bil24_order_id=555,
        ticket_amount_minor=1000,
        service_fee_amount_minor=250,
        gross_amount_minor=1250,
        platform_fee_amount_minor=None,
        payment_type="bill24_acquiring",
        payment_provider=None,
        payment_url=None,
        stripe_session_id=None,
        stripe_payment_intent_id=None,
        stripe_application_fee_amount_minor=None,
    )
    agent = SimpleNamespace(
        id=77,
        payment_type="stripe_connect",
        stripe_account_id="acct_123",
        stripe_charges_enabled=True,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order), _scalar_result(agent)]

    stripe_client = MagicMock()
    stripe_client.checkout.Session.create.side_effect = Exception("network down")

    with patch("app.api.payments.async_session_maker", return_value=DummySessionContext(db)):
        with patch("app.api.payments._get_stripe_client", return_value=stripe_client):
            with patch(
                "app.api.payments.get_admin_risk_settings",
                new_callable=AsyncMock,
                return_value={"payment_success_url": "https://example.com"},
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await create_checkout_session(CreateSessionRequest(order_id=123))

    assert exc_info.value.status_code == 502
    assert "Stripe checkout session creation failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_checkout_session_rejects_unready_connect_agent():
    from app.api.payments import CreateSessionRequest, create_checkout_session

    order = SimpleNamespace(
        id=123,
        status="NEW",
        total_sum=Decimal("12.50"),
        currency="USD",
        agent_id=77,
    )
    agent = SimpleNamespace(
        id=77,
        payment_type="stripe_connect",
        stripe_account_id="acct_123",
        stripe_charges_enabled=False,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order), _scalar_result(agent)]

    with patch("app.api.payments.async_session_maker", return_value=DummySessionContext(db)):
        with patch("app.api.payments._get_stripe_client", return_value=MagicMock()):
            with patch(
                "app.api.payments.get_admin_risk_settings",
                new_callable=AsyncMock,
                return_value={"payment_success_url": "https://example.com"},
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await create_checkout_session(CreateSessionRequest(order_id=123))

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("status_value", ["restricted", "blocked", "force_blocked"])
async def test_create_checkout_session_rejects_non_sellable_agent_status(status_value: str):
    from app.api.payments import CreateSessionRequest, create_checkout_session

    order = SimpleNamespace(
        id=123,
        status="NEW",
        total_sum=Decimal("12.50"),
        currency="USD",
        agent_id=77,
    )
    agent = SimpleNamespace(
        id=77,
        is_active=True,
        agent_operational_status=status_value,
        payment_type="stripe_connect",
        stripe_account_id="acct_123",
        stripe_charges_enabled=True,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order), _scalar_result(agent)]

    with patch("app.api.payments.async_session_maker", return_value=DummySessionContext(db)):
        with patch("app.api.payments._get_stripe_client", return_value=MagicMock()):
            with patch(
                "app.api.payments.get_admin_risk_settings",
                new_callable=AsyncMock,
                return_value={"payment_success_url": "https://example.com"},
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await create_checkout_session(CreateSessionRequest(order_id=123))

    assert exc_info.value.status_code == 409
    assert status_value in exc_info.value.detail
