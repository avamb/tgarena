"""Tests for refund calculation and webhook case creation."""

import os
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.mark.asyncio
async def test_calculate_refund_supports_full_and_ticket_only_modes():
    from app.services.refunds import calculate_refund

    order = SimpleNamespace(
        id=15,
        refund_total_minor=0,
        currency="USD",
        total_sum="100.00",
        ticket_amount_minor=8500,
        gross_amount_minor=10000,
    )
    db = SimpleNamespace(add=MagicMock(), flush=AsyncMock())

    full_refund = await calculate_refund(
        order=order,
        mode="full_refund",
        reason="customer_request",
        db=db,
    )
    ticket_only_refund = await calculate_refund(
        order=order,
        mode="ticket_only_refund",
        reason="event_change",
        db=db,
    )

    assert full_refund.customer_refund_amount_minor == 10000
    assert full_refund.ticket_refund_amount_minor == 8500
    assert full_refund.service_fee_refund_amount_minor == 1500
    assert ticket_only_refund.customer_refund_amount_minor == 8500
    assert ticket_only_refund.service_fee_refund_amount_minor == 0


@pytest.mark.asyncio
async def test_create_refund_case_from_webhook_allocates_ticket_then_fee():
    from app.services.refunds import create_refund_case_from_webhook

    order = SimpleNamespace(
        id=22,
        agent_id=5,
        currency="USD",
        refund_total_minor=2000,
        total_sum="100.00",
        ticket_amount_minor=8000,
        gross_amount_minor=10000,
    )
    db = SimpleNamespace(add=MagicMock(), flush=AsyncMock())

    refund_case = await create_refund_case_from_webhook(
        order=order,
        refund_amount_minor=3000,
        stripe_refund_id="re_123",
        reason="stripe charge.refunded webhook",
        db=db,
    )

    assert refund_case.order_id == 22
    assert refund_case.ticket_refund_amount_minor == 3000
    assert refund_case.service_fee_refund_amount_minor == 0
    assert refund_case.agent_debit_amount_minor == 3000
    db.add.assert_called_once()
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_refund_case_from_webhook_updates_existing_processing_case():
    from app.models import RefundCaseStatus
    from app.services.refunds import create_refund_case_from_webhook

    order = SimpleNamespace(
        id=33,
        agent_id=8,
        currency="USD",
        refund_total_minor=0,
        total_sum="100.00",
        ticket_amount_minor=8000,
        gross_amount_minor=10000,
    )
    existing_refund_case = SimpleNamespace(
        id=501,
        order_id=33,
        agent_id=8,
        currency="USD",
        customer_refund_amount_minor=0,
        ticket_refund_amount_minor=0,
        service_fee_refund_amount_minor=0,
        platform_cost_amount_minor=0,
        agent_debit_amount_minor=0,
        stripe_refund_id="re_existing",
        status=RefundCaseStatus.PROCESSING.value,
        reason=None,
        completed_at=None,
    )

    refund_case_result = MagicMock()
    refund_case_result.scalar_one_or_none.return_value = existing_refund_case
    db = SimpleNamespace(
        add=MagicMock(),
        flush=AsyncMock(),
        execute=AsyncMock(return_value=refund_case_result),
    )

    refund_case = await create_refund_case_from_webhook(
        order=order,
        refund_amount_minor=2500,
        stripe_refund_id="re_existing",
        reason="stripe charge.refunded webhook",
        db=db,
    )

    assert refund_case is existing_refund_case
    assert refund_case.customer_refund_amount_minor == 2500
    assert refund_case.status == RefundCaseStatus.COMPLETED.value
    db.add.assert_not_called()
    db.flush.assert_awaited_once()
