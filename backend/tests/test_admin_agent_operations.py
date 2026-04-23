"""Tests for admin agent risk operations endpoints."""

import os
from datetime import datetime
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_all_result(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


@pytest.mark.asyncio
async def test_top_up_agent_wallet_returns_updated_wallet():
    from app.api.admin import AgentTopUpRequest, top_up_agent_wallet

    agent = SimpleNamespace(id=77, agent_operational_status="warning")
    wallet = SimpleNamespace(
        id=501,
        agent_id=77,
        currency="USD",
        reserve_balance_minor=3000,
        credit_limit_minor=1000,
        negative_exposure_minor=500,
        warning_threshold_minor=1000,
        block_threshold_minor=2500,
        status="active",
        last_warning_at=None,
        last_blocked_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    policy = SimpleNamespace(
        min_reserve_balance_minor=0,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(agent)]

    with patch(
        "app.api.admin.post_entry",
        new_callable=AsyncMock,
        return_value=SimpleNamespace(id=901),
    ) as mock_post_entry:
        with patch(
            "app.api.admin.get_wallet_for_agent_currency",
            new_callable=AsyncMock,
            return_value=wallet,
        ):
            with patch("app.api.admin.evaluate_agent_risk", new_callable=AsyncMock):
                with patch(
                    "app.api.admin.ensure_risk_policy",
                    new_callable=AsyncMock,
                    return_value=policy,
                ):
                    response = await top_up_agent_wallet(
                        agent_id=77,
                        payload=AgentTopUpRequest(currency="usd", amount_minor=2500, description="Recovery"),
                        current_user=SimpleNamespace(id=1),
                        db=db,
                    )

    mock_post_entry.assert_awaited_once()
    assert response.agent_id == 77
    assert response.entry_id == 901
    assert response.wallet.currency == "USD"
    assert response.wallet.reserve_balance_minor == 3000


@pytest.mark.asyncio
async def test_force_block_agent_sets_manual_override():
    from app.api.admin import force_block_agent

    agent = SimpleNamespace(id=77, agent_operational_status="active")
    policy = SimpleNamespace(manual_override_status=None)

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(agent)]

    with patch(
        "app.api.admin.ensure_risk_policy",
        new_callable=AsyncMock,
        return_value=policy,
    ):
        response = await force_block_agent(
            agent_id=77,
            current_user=SimpleNamespace(id=1),
            db=db,
        )

    assert policy.manual_override_status == "force_blocked"
    assert response.agent_operational_status == "force_blocked"
    assert response.manual_override_status == "force_blocked"


@pytest.mark.asyncio
async def test_unblock_agent_recalculates_status_from_wallets():
    from app.api.admin import unblock_agent

    agent = SimpleNamespace(id=77, agent_operational_status="force_blocked")
    wallet = SimpleNamespace(id=501, currency="USD")
    policy = SimpleNamespace(manual_override_status="force_blocked")

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(agent), _scalars_all_result([wallet])]

    async def _evaluate(agent, wallet, db, policy):
        agent.agent_operational_status = "active"
        return SimpleNamespace(status="active")

    with patch(
        "app.api.admin.ensure_risk_policy",
        new_callable=AsyncMock,
        return_value=policy,
    ):
        with patch("app.api.admin.evaluate_agent_risk", side_effect=_evaluate) as mock_evaluate:
            response = await unblock_agent(
                agent_id=77,
                current_user=SimpleNamespace(id=1),
                db=db,
            )

    mock_evaluate.assert_awaited_once()
    assert policy.manual_override_status is None
    assert response.agent_operational_status == "active"
    assert response.manual_override_status is None
