"""Money helpers for settlement and Stripe Connect flows."""

from decimal import Decimal, ROUND_HALF_UP


CURRENCY_EXPONENTS = {
    "BHD": 3,
    "EUR": 2,
    "GBP": 2,
    "ILS": 2,
    "JPY": 0,
    "KWD": 3,
    "RUB": 2,
    "USD": 2,
}


def normalize_currency(code: str) -> str:
    """Return an uppercase ISO-like currency code."""
    normalized = (code or "").strip().upper()
    if not normalized:
        raise ValueError("Currency code is required")
    return normalized


def get_currency_exponent(currency: str) -> int:
    """Return decimal exponent for a currency."""
    normalized = normalize_currency(currency)
    return CURRENCY_EXPONENTS.get(normalized, 2)


def to_minor(amount: Decimal | float | int | str, currency: str) -> int:
    """Convert a major-unit amount into integer minor units."""
    exponent = get_currency_exponent(currency)
    quant = Decimal("1").scaleb(-exponent)
    decimal_amount = Decimal(str(amount)).quantize(quant, rounding=ROUND_HALF_UP)
    multiplier = Decimal(10) ** exponent
    return int((decimal_amount * multiplier).to_integral_value(rounding=ROUND_HALF_UP))


def from_minor(amount_minor: int, currency: str) -> Decimal:
    """Convert integer minor units into a major-unit Decimal."""
    exponent = get_currency_exponent(currency)
    divisor = Decimal(10) ** exponent
    return Decimal(amount_minor) / divisor
