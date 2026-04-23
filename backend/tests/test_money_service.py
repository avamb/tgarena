"""Tests for settlement money helpers."""

from decimal import Decimal
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_to_minor_rounds_half_up():
    from app.services.money import to_minor

    assert to_minor(Decimal("10.555"), "USD") == 1056


def test_to_minor_supports_zero_decimal_currency():
    from app.services.money import to_minor

    assert to_minor(Decimal("125"), "JPY") == 125


def test_from_minor_restores_major_units():
    from app.services.money import from_minor

    assert from_minor(1050, "ILS") == Decimal("10.5")


def test_normalize_currency_uppercases_values():
    from app.services.money import normalize_currency

    assert normalize_currency(" usd ") == "USD"
