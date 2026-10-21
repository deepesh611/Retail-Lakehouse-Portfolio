"""Feature helpers for churn modeling (pure Python where possible for unit tests)."""

from __future__ import annotations

from typing import Any

FEATURE_COLUMNS = [
    "order_count",
    "lifetime_revenue",
    "avg_order_value",
    "event_count",
    "purchase_events",
    "days_since_last_order",
    "region_north",
    "region_south",
    "region_east",
    "region_west",
    "region_central",
    "tier_bronze",
    "tier_silver",
    "tier_gold",
    "tier_platinum",
]

LABEL_COLUMN = "churn_label"


def one_hot_region(region: str | None) -> dict[str, int]:
    regions = ["north", "south", "east", "west", "central"]
    r = (region or "").lower()
    return {f"region_{name}": int(r == name) for name in regions}


def one_hot_tier(tier: str | None) -> dict[str, int]:
    tiers = ["bronze", "silver", "gold", "platinum"]
    t = (tier or "").lower()
    return {f"tier_{name}": int(t == name) for name in tiers}


def _as_float(value: Any, default: float = 0.0) -> float:
    """Coerce Spark/pandas nulls and NaN to a finite float."""
    if value is None:
        return default
    try:
        # pandas / numpy NaN are truthy, so `value or default` is unsafe
        import math

        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except (TypeError, ValueError):
        return default


def row_to_features(row: dict[str, Any]) -> dict[str, float]:
    """Convert a gold_customer_360-like dict into model features."""
    feats: dict[str, float] = {
        "order_count": _as_float(row.get("order_count"), 0.0),
        "lifetime_revenue": _as_float(row.get("lifetime_revenue"), 0.0),
        "avg_order_value": _as_float(row.get("avg_order_value"), 0.0),
        "event_count": _as_float(row.get("event_count"), 0.0),
        "purchase_events": _as_float(row.get("purchase_events"), 0.0),
        "days_since_last_order": _as_float(row.get("days_since_last_order"), 999.0),
    }
    feats.update({k: float(v) for k, v in one_hot_region(row.get("region")).items()})
    feats.update({k: float(v) for k, v in one_hot_tier(row.get("loyalty_tier")).items()})
    return feats


def feature_vector(row: dict[str, Any]) -> list[float]:
    feats = row_to_features(row)
    return [feats[c] for c in FEATURE_COLUMNS]
