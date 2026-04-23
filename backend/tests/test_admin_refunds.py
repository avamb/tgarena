"""Tests for admin refund calculation and execution endpoints."""

import os
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_calculate_order_refund_returns_breakdown_from_service():
    from app.api.admin import (
        RefundCalculateRequest,
        calculate_order_refund,
    )

    order = SimpleNamespace(
        id=123,
        agent_id=77,
        currency="USD",
        status="PAID",
    )
    calculation = SimpleNamespace(
        customer_refund_amount_minor=5000,
        ticket_refund_amount_minor=4500,
        service_fee_refund_amount_minor=500,
        platform_cost_amount_minor=0,
        agent_debit_amount_minor=5000,
        post_refund_status="warning",
        top_up_required_minor=700,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order)]

    with patch("app.api.admin.calculate_refund", new_callable=AsyncMock, return_value=calculation) as mock_calculate:
        response = await calculate_order_refund(
            order_id=123,
            payload=RefundCalculateRequest(mode="custom_partial_refund", amount_minor=5000, reason="customer_request"),
            current_user=SimpleNamespace(id=1),
            db=db,
        )

    mock_calculate.assert_awaited_once()
    assert response.order_id == 123
    assert response.customer_refund_amount_minor == 5000
    assert response.post_refund_status == "warning"
    assert response.top_up_required_minor == 700


@pytest.mark.asyncio
async def test_execute_order_refund_submits_to_stripe_and_creates_processing_case():
    from app.api.admin import (
        RefundExecuteRequest,
        execute_order_refund,
    )

    order = SimpleNamespace(
        id=123,
        agent_id=77,
        currency="USD",
        status="PAID",
        risk_state=None,
        stripe_charge_id="ch_123",
        payment_type="stripe_connect",
        payment_provider="stripe_connect",
    )
    calculation = SimpleNamespace(
        customer_refund_amount_minor=5000,
        ticket_refund_amount_minor=4500,
        service_fee_refund_amount_minor=500,
        platform_cost_amount_minor=0,
        agent_debit_amount_minor=5000,
        post_refund_status="warning",
        top_up_required_minor=700,
    )
    refund_case = SimpleNamespace(
        id=901,
        order_id=123,
        agent_id=77,
        currency="USD",
        customer_refund_amount_minor=5000,
        ticket_refund_amount_minor=4500,
        service_fee_refund_amount_minor=500,
        platform_cost_amount_minor=0,
        agent_debit_amount_minor=5000,
        stripe_refund_id="re_123",
        status="processing",
        policy_applied="custom_partial_refund",
        reason="customer_request",
        created_at="2026-04-21T00:00:00",
        completed_at=None,
    )

    db = AsyncMock()
    db.execute.side_effect = [_scalar_result(order)]

    with patch("app.api.admin.calculate_refund", new_callable=AsyncMock, return_value=calculation):
        with patch("app.api.admin.ensure_order_charge_id", new_callable=AsyncMock) as mock_ensure_charge:
            with patch(
                "app.api.admin.create_order_refund",
                return_value=SimpleNamespace(id="re_123", status="pending"),
            ) as mock_create_refund:
                with patch(
                    "app.api.admin.create_pending_refund_case",
                    new_callable=AsyncMock,
                    return_value=refund_case,
                ) as mock_create_case:
                    response = await execute_order_refund(
                        order_id=123,
                        payload=RefundExecuteRequest(
                            mode="custom_partial_refund",
                            amount_minor=5000,
                            reason="customer_request",
                        ),
                        current_user=SimpleNamespace(id=1),
                        db=db,
                    )

    mock_ensure_charge.assert_awaited_once_with(order=order, db=db)
    mock_create_refund.assert_called_once()
    mock_create_case.assert_awaited_once()
    assert order.risk_state == "refund_submitted"
    assert response.stripe_refund_status == "pending"
    assert response.refund_case.id == 901
