"""Tests for admin Stripe Connect endpoints."""

import os
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_create_agent_stripe_account_creates_connected_account_when_missing():
    from app.api.admin import create_agent_stripe_account

    agent = SimpleNamespace(
        id=77,
        payment_type="bill24_acquiring",
        stripe_account_id=None,
        stripe_account_status=None,
        stripe_charges_enabled=False,
        stripe_payouts_enabled=False,
    )
    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(agent)]

    with patch("app.api.admin.create_connected_account", new_callable=AsyncMock) as mock_create_account:
        response = await create_agent_stripe_account(
            agent_id=77,
            current_user=SimpleNamespace(id=1),
            db=db,
        )

    mock_create_account.assert_awaited_once_with(agent=agent, db=db)
    assert response.agent_id == 77


@pytest.mark.asyncio
async def test_create_agent_stripe_onboarding_link_uses_rollout_urls_by_default():
    from app.api.admin import StripeOnboardingLinkRequest, create_agent_stripe_onboarding_link

    agent = SimpleNamespace(
        id=77,
        payment_type="stripe_connect",
        stripe_account_id="acct_123",
        stripe_account_status="pending_onboarding",
        stripe_charges_enabled=False,
        stripe_payouts_enabled=False,
    )
    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(agent)]

    with patch(
        "app.api.admin.get_admin_risk_settings",
        new_callable=AsyncMock,
        return_value={
            "payment_success_url": "https://example.com/pay",
            "stripe_connect_refresh_url": "https://example.com/refresh",
            "stripe_connect_return_url": "https://example.com/return",
        },
    ):
        with patch(
            "app.api.admin.create_onboarding_link",
            return_value=SimpleNamespace(url="https://connect.stripe.test/onboarding"),
        ) as mock_create_link:
            response = await create_agent_stripe_onboarding_link(
                agent_id=77,
                payload=StripeOnboardingLinkRequest(),
                current_user=SimpleNamespace(id=1),
                db=db,
            )

    mock_create_link.assert_called_once_with(
        agent=agent,
        refresh_url="https://example.com/refresh",
        return_url="https://example.com/return",
    )
    assert response.agent_id == 77
    assert response.onboarding_url == "https://connect.stripe.test/onboarding"


@pytest.mark.asyncio
async def test_get_agent_stripe_status_returns_502_on_unexpected_stripe_error():
    from app.api.admin import get_agent_stripe_status

    agent = SimpleNamespace(
        id=77,
        payment_type="stripe_connect",
        stripe_account_id="acct_123",
        stripe_account_status="pending_onboarding",
        stripe_charges_enabled=False,
        stripe_payouts_enabled=False,
    )
    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(agent)]

    with patch(
        "app.api.admin.refresh_account_status",
        new_callable=AsyncMock,
        side_effect=Exception("stripe api unavailable"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_agent_stripe_status(
                agent_id=77,
                current_user=SimpleNamespace(id=1),
                db=db,
            )

    assert exc_info.value.status_code == 502
    assert "Stripe status refresh failed" in exc_info.value.detail
