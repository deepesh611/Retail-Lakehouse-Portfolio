"""Compare challenger vs champion; promote alias if thresholds pass."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


DEFAULT_THRESHOLDS = {
    "min_roc_auc": 0.60,
    "min_f1": 0.40,
    "min_improvement_roc_auc": 0.0,
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--model-name", required=True)
    p.add_argument("--min-roc-auc", type=float, default=DEFAULT_THRESHOLDS["min_roc_auc"])
    p.add_argument("--min-f1", type=float, default=DEFAULT_THRESHOLDS["min_f1"])
    p.add_argument(
        "--min-improvement-roc-auc",
        type=float,
        default=DEFAULT_THRESHOLDS["min_improvement_roc_auc"],
    )
    p.add_argument("--audit-table", default="ml_promotion_audit")
    return p.parse_args()


def _run_metric(client, run_id: str, key: str) -> float | None:
    run = client.get_run(run_id)
    val = run.data.metrics.get(key)
    return float(val) if val is not None else None


def decide_promotion(
    challenger_metrics: dict[str, float | None],
    champion_metrics: dict[str, float | None] | None,
    min_roc_auc: float,
    min_f1: float,
    min_improvement: float,
) -> tuple[bool, str]:
    roc = challenger_metrics.get("roc_auc")
    f1 = challenger_metrics.get("f1")
    if roc is None or f1 is None:
        return False, "missing_challenger_metrics"
    if roc < min_roc_auc:
        return False, f"roc_auc_below_threshold:{roc:.4f}<{min_roc_auc}"
    if f1 < min_f1:
        return False, f"f1_below_threshold:{f1:.4f}<{min_f1}"
    if champion_metrics and champion_metrics.get("roc_auc") is not None:
        champ_roc = champion_metrics["roc_auc"] or 0.0
        if roc + 1e-12 < champ_roc + min_improvement:
            return False, f"no_improvement_vs_champion:{roc:.4f}<={champ_roc:.4f}"
    return True, "thresholds_passed"


def main() -> None:
    from mlflow.tracking import MlflowClient

    args = _parse_args()
    client = MlflowClient()

    challenger = client.get_model_version_by_alias(args.model_name, "challenger")
    challenger_metrics = {
        "roc_auc": _run_metric(client, challenger.run_id, "roc_auc"),
        "f1": _run_metric(client, challenger.run_id, "f1"),
        "accuracy": _run_metric(client, challenger.run_id, "accuracy"),
    }

    champion_metrics = None
    champion_version = None
    try:
        champion = client.get_model_version_by_alias(args.model_name, "champion")
        champion_version = champion.version
        champion_metrics = {
            "roc_auc": _run_metric(client, champion.run_id, "roc_auc"),
            "f1": _run_metric(client, champion.run_id, "f1"),
            "accuracy": _run_metric(client, champion.run_id, "accuracy"),
        }
    except Exception:
        champion_metrics = None

    promote, reason = decide_promotion(
        challenger_metrics,
        champion_metrics,
        args.min_roc_auc,
        args.min_f1,
        args.min_improvement_roc_auc,
    )

    if promote:
        client.set_registered_model_alias(
            args.model_name, "champion", challenger.version
        )

    record = {
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "model_name": args.model_name,
        "challenger_version": challenger.version,
        "champion_version_before": champion_version,
        "promoted": promote,
        "reason": reason,
        "challenger_roc_auc": challenger_metrics.get("roc_auc"),
        "challenger_f1": challenger_metrics.get("f1"),
        "champion_roc_auc": (champion_metrics or {}).get("roc_auc"),
    }

    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    audit_table = f"{args.catalog}.{args.schema}.{args.audit_table}"
    spark.createDataFrame([record]).write.mode("append").option(
        "mergeSchema", "true"
    ).saveAsTable(audit_table)

    print(json.dumps(record))


if __name__ == "__main__":
    main()
