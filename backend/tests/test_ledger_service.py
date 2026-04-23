"""Tests for ledger-derived wallet state."""

import os
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_calculate_wallet_state_tracks_reserve_and_exposure():
    from app.services.ledger import calculate_wallet_state

    entries = [
        SimpleNamespace(direction="credit", amount_minor=5000, entry_type="sale"),
        SimpleNamespace(direction="debit", amount_minor=7000, entry_type="refund"),
        SimpleNamespace(direction="credit", amount_minor=2000, entry_type="top_up"),
    ]

    state = calculate_wallet_state(
        entries=entries,
        credit_limit_minor=1000,
        warning_threshold_minor=1000,
        block_threshold_minor=3000,
    )

    assert state["reserve_balance_minor"] == 2000
    assert state["negative_exposure_minor"] == 0
    assert state["status"] == "active"


def test_calculate_wallet_state_blocks_when_exposure_crosses_threshold():
    from app.services.ledger import calculate_wallet_state

    entries = [
        SimpleNamespace(direction="debit", amount_minor=4500, entry_type="refund"),
    ]

    state = calculate_wallet_state(
        entries=entries,
        credit_limit_minor=0,
        warning_threshold_minor=1000,
        block_threshold_minor=3000,
    )

    assert state["negative_exposure_minor"] == 4500
    assert state["status"] == "blocked"


def test_build_sale_postings_creates_sale_platform_fee_and_processing_entries():
    from app.services.ledger import build_sale_postings

    order = SimpleNamespace(
        id=42,
        agent_id=7,
        currency="USD",
        total_sum="100.00",
        ticket_amount_minor=9000,
        gross_amount_minor=10000,
        platform_fee_amount_minor=1000,
        stripe_fee_estimated_minor=350,
    )

    postings = build_sale_postings(
        order=order,
        source="stripe_webhook_sale",
        source_id="evt_sale_1",
    )

    assert [posting.entry_type for posting in postings] == [
        "sale",
        "platform_fee",
        "stripe_fee_estimate",
    ]
    assert [posting.direction for posting in postings] == ["credit", "credit", "debit"]
    assert [posting.amount_minor for posting in postings] == [9000, 1000, 350]


@pytest.mark.asyncio
async def test_post_entries_idempotent_reuses_existing_entry_without_wallet_rebuild():
    from app.services.ledger import LedgerPosting, post_entries

    posting = LedgerPosting(
        agent_id=7,
        currency="USD",
        amount_minor=9000,
        direction="credit",
        entry_type="sale",
        order_id=42,
        source="stripe_webhook_sale",
        source_id="evt_sale_1",
    )
    existing_entry = SimpleNamespace(id=501, wallet_id=12)
    db = AsyncMock()

    with patch(
        "app.services.ledger._find_existing_entry",
        new_callable=AsyncMock,
        return_value=existing_entry,
    ) as mock_find_existing:
        with patch("app.services.ledger.ensure_wallet_exists", new_callable=AsyncMock) as mock_ensure_wallet:
            with patch("app.services.ledger.rebuild_wallet_from_ledger", new_callable=AsyncMock) as mock_rebuild_wallet:
                entries = await post_entries([posting], db=db, idempotent=True)

    assert entries == [existing_entry]
    mock_find_existing.assert_awaited_once()
    mock_ensure_wallet.assert_not_awaited()
    mock_rebuild_wallet.assert_not_awaited()
    db.add.assert_not_called()
