"""Helpers for persisting admin-managed rollout settings in system_settings."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.core.config import settings
    from app.models import SystemSetting
except ModuleNotFoundError:
    from backend.app.core.config import settings
    from backend.app.models import SystemSetting


SYSTEM_SETTING_SPECS: dict[str, dict[str, Any]] = {
    "allow_negative_balance": {
        "key": "risk_allow_negative_balance",
        "default": True,
        "description": "Default risk policy: allow agent negative balance",
        "cast": "bool",
    },
    "auto_block_enabled": {
        "key": "risk_auto_block_enabled",
        "default": True,
        "description": "Default risk policy: enable automatic blocking",
        "cast": "bool",
    },
    "refund_window_days": {
        "key": "risk_refund_window_days",
        "default": 30,
        "description": "Default refund event rolling window in days",
        "cast": "int",
    },
    "refund_event_warning_count": {
        "key": "risk_refund_event_warning_count",
        "default": 3,
        "description": "Default refund event count that triggers warning status",
        "cast": "int",
    },
    "refund_event_block_count": {
        "key": "risk_refund_event_block_count",
        "default": 7,
        "description": "Default refund event count that triggers block status",
        "cast": "int",
    },
    "rolling_reserve_percent_bps": {
        "key": "risk_rolling_reserve_percent_bps",
        "default": 0,
        "description": "Default rolling reserve hold in basis points",
        "cast": "int",
    },
    "min_reserve_balance_minor": {
        "key": "risk_min_reserve_balance_minor",
        "default": 0,
        "description": "Default minimum reserve balance in minor units",
        "cast": "int",
    },
    "default_credit_limit_minor": {
        "key": "risk_default_credit_limit_minor",
        "default": 0,
        "description": "Default wallet credit limit in minor units",
        "cast": "int",
    },
    "payment_success_url": {
        "key": "payment_success_url",
        "default": settings.PAYMENT_SUCCESS_URL or "https://tgtest.arenasoldout.com",
        "description": "Checkout return URL after successful payment",
        "cast": "str",
    },
    "stripe_connect_return_url": {
        "key": "stripe_connect_return_url",
        "default": settings.STRIPE_CONNECT_RETURN_URL or "",
        "description": "Stripe Connect onboarding return URL",
        "cast": "str",
    },
    "stripe_connect_refresh_url": {
        "key": "stripe_connect_refresh_url",
        "default": settings.STRIPE_CONNECT_REFRESH_URL or "",
        "description": "Stripe Connect onboarding refresh URL",
        "cast": "str",
    },
    "telegram_bot_username": {
        "key": "telegram_bot_username",
        "default": settings.TELEGRAM_BOT_USERNAME or "",
        "description": "Telegram bot username for deep links and payment redirects",
        "cast": "str",
    },
    "default_zone": {
        "key": "default_zone",
        "default": "test",
        "description": "Default Bill24 zone for newly created agents",
        "cast": "str",
    },
    "event_cache_ttl": {
        "key": "event_cache_ttl",
        "default": int(settings.EVENT_CACHE_TTL or 900),
        "description": "Bill24 event cache TTL in seconds",
        "cast": "int",
    },
    "webhook_url": {
        "key": "webhook_url",
        "default": "",
        "description": "Admin-configured outbound webhook endpoint URL",
        "cast": "str",
    },
}


def _coerce_bool(value: str, default: bool) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _coerce_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_value(raw_value: str, *, cast: str, default: Any) -> Any:
    if cast == "bool":
        return _coerce_bool(raw_value, bool(default))
    if cast == "int":
        return _coerce_int(raw_value, int(default))
    return str(raw_value)


def _serialize_value(value: Any, *, cast: str) -> str:
    if cast == "bool":
        return "true" if bool(value) else "false"
    return str(value)


async def _fetch_settings_by_key(
    db: AsyncSession,
    keys: list[str],
) -> dict[str, SystemSetting]:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key.in_(keys)))
    rows = result.scalars().all()
    return {row.key: row for row in rows}


async def get_admin_risk_settings(db: AsyncSession) -> dict[str, Any]:
    """Return rollout settings exposed to the admin settings page."""
    keys = [spec["key"] for spec in SYSTEM_SETTING_SPECS.values()]
    rows = await _fetch_settings_by_key(db=db, keys=keys)

    payload: dict[str, Any] = {}
    for field_name, spec in SYSTEM_SETTING_SPECS.items():
        row = rows.get(spec["key"])
        if row is None:
            payload[field_name] = spec["default"]
            continue
        payload[field_name] = _coerce_value(
            row.value,
            cast=str(spec["cast"]),
            default=spec["default"],
        )

    payment_success_url = str(payload["payment_success_url"]).strip()
    default_base_url = payment_success_url or "https://tgtest.arenasoldout.com"
    payload["payment_success_url"] = default_base_url
    payload["stripe_connect_return_url"] = (
        str(payload["stripe_connect_return_url"]).strip() or default_base_url
    )
    payload["stripe_connect_refresh_url"] = (
        str(payload["stripe_connect_refresh_url"]).strip() or default_base_url
    )
    payload["telegram_bot_username"] = str(payload["telegram_bot_username"]).strip()
    payload["default_zone"] = str(payload["default_zone"]).strip() or "test"
    return payload


async def save_admin_risk_settings(
    db: AsyncSession,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Persist rollout settings passed from the admin settings page."""
    rows = await _fetch_settings_by_key(
        db=db,
        keys=[
            SYSTEM_SETTING_SPECS[field_name]["key"]
            for field_name in updates.keys()
            if field_name in SYSTEM_SETTING_SPECS
        ],
    )

    for field_name, value in updates.items():
        if field_name not in SYSTEM_SETTING_SPECS:
            continue
        spec = SYSTEM_SETTING_SPECS[field_name]
        key = str(spec["key"])
        serialized = _serialize_value(value, cast=str(spec["cast"]))
        row = rows.get(key)
        if row is None:
            row = SystemSetting(
                key=key,
                value=serialized,
                description=str(spec["description"]),
            )
            db.add(row)
            rows[key] = row
        else:
            row.value = serialized
            row.description = str(spec["description"])

    await db.flush()
    return await get_admin_risk_settings(db=db)


async def get_risk_policy_defaults(db: AsyncSession) -> dict[str, Any]:
    settings_payload = await get_admin_risk_settings(db=db)
    return {
        "allow_negative_balance": bool(settings_payload["allow_negative_balance"]),
        "auto_block_enabled": bool(settings_payload["auto_block_enabled"]),
        "refund_window_days": int(settings_payload["refund_window_days"]),
        "refund_event_warning_count": int(settings_payload["refund_event_warning_count"]),
        "refund_event_block_count": int(settings_payload["refund_event_block_count"]),
        "rolling_reserve_percent_bps": int(settings_payload["rolling_reserve_percent_bps"]),
        "min_reserve_balance_minor": int(settings_payload["min_reserve_balance_minor"]),
    }


async def get_default_wallet_credit_limit_minor(db: AsyncSession) -> int:
    settings_payload = await get_admin_risk_settings(db=db)
    return int(settings_payload["default_credit_limit_minor"])

