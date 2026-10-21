from __future__ import annotations

from src.ml.features import FEATURE_COLUMNS, feature_vector, row_to_features


def test_row_to_features_shape():
    row = {
        "order_count": 3,
        "lifetime_revenue": 120.5,
        "avg_order_value": 40.1,
        "event_count": 10,
        "purchase_events": 2,
        "days_since_last_order": 45,
        "region": "north",
        "loyalty_tier": "gold",
    }
    feats = row_to_features(row)
    assert feats["region_north"] == 1.0
    assert feats["region_south"] == 0.0
    assert feats["tier_gold"] == 1.0
    vec = feature_vector(row)
    assert len(vec) == len(FEATURE_COLUMNS)
    assert vec[FEATURE_COLUMNS.index("order_count")] == 3.0


def test_missing_days_defaults_high():
    feats = row_to_features({"region": "east", "loyalty_tier": "bronze"})
    assert feats["days_since_last_order"] == 999.0


def test_nan_coerced_to_defaults():
    feats = row_to_features(
        {
            "order_count": float("nan"),
            "lifetime_revenue": float("nan"),
            "days_since_last_order": float("nan"),
            "region": "west",
            "loyalty_tier": "silver",
        }
    )
    assert feats["order_count"] == 0.0
    assert feats["lifetime_revenue"] == 0.0
    assert feats["days_since_last_order"] == 999.0
    assert feats["region_west"] == 1.0
