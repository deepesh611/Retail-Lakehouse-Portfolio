from __future__ import annotations

from src.ml.promote import decide_promotion


def test_promote_when_thresholds_pass():
    ok, reason = decide_promotion(
        {"roc_auc": 0.8, "f1": 0.7},
        {"roc_auc": 0.7, "f1": 0.6},
        min_roc_auc=0.6,
        min_f1=0.4,
        min_improvement=0.0,
    )
    assert ok is True
    assert reason == "thresholds_passed"


def test_reject_low_roc():
    ok, reason = decide_promotion(
        {"roc_auc": 0.5, "f1": 0.9},
        None,
        min_roc_auc=0.6,
        min_f1=0.4,
        min_improvement=0.0,
    )
    assert ok is False
    assert "roc_auc_below_threshold" in reason


def test_reject_no_improvement():
    ok, reason = decide_promotion(
        {"roc_auc": 0.71, "f1": 0.7},
        {"roc_auc": 0.75, "f1": 0.7},
        min_roc_auc=0.6,
        min_f1=0.4,
        min_improvement=0.0,
    )
    assert ok is False
    assert "no_improvement" in reason
