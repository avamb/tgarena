"""Tests for risk engine decisions."""

import os
from types import SimpleNamespace
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_evaluate_wallet_status_blocks_on_wallet_or_refund_threshold():
    from app.services.risk_engine import evaluate_wallet_status

    wallet = SimpleNamespace(
        status="warning",
        reserve_balance_minor=0,
        credit_limit_minor=0,
        negative_exposure_minor=100,
    )
    policy = SimpleNamespace(
        allow_negative_balance=True,
        auto_block_enabled=True,
        refund_event_warning_count=2,
        refund_event_block_count=3,
        manual_override_status=None,
    )

    status = evaluate_wallet_status(wallet=wallet, policy=policy, refund_event_count=3)

    assert status == "blocked"


def test_evaluate_wallet_status_honors_manual_override():
    from app.services.risk_engine import evaluate_wallet_status

    wallet = SimpleNamespace(
        status="blocked",
        reserve_balance_minor=0,
        credit_limit_minor=0,
        negative_exposure_minor=5000,
    )
    policy = SimpleNamespace(
        allow_negative_balance=False,
        auto_block_enabled=True,
        refund_event_warning_count=1,
        refund_event_block_count=2,
        manual_override_status="force_blocked",
    )

    status = evaluate_wallet_status(wallet=wallet, policy=policy, refund_event_count=0)

    assert status == "force_blocked"


def test_calculate_top_up_required_uses_capacity_and_min_reserve():
    from app.services.risk_engine import calculate_top_up_required

    wallet = SimpleNamespace(
        reserve_balance_minor=1000,
        credit_limit_minor=500,
        negative_exposure_minor=2500,
    )
    policy = SimpleNamespace(
        min_reserve_balance_minor=2000,
    )

    top_up_required_minor = calculate_top_up_required(wallet=wallet, policy=policy)

    assert top_up_required_minor == 1000
