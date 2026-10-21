"""Batch-score current customers with the champion model into gold.churn_predictions."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

from features import FEATURE_COLUMNS, row_to_features


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--model-name", required=True)
    p.add_argument("--source-table", default="gold_customer_360")
    p.add_argument("--target-table", default="churn_predictions")
    p.add_argument("--alias", default="champion")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    source = args.source_table
    if source.count(".") == 0:
        source = f"{args.catalog}.{args.schema}.{source}"
    target = f"{args.catalog}.{args.schema}.{args.target_table}"

    client = MlflowClient()
    mv = client.get_model_version_by_alias(args.model_name, args.alias)
    model_uri = f"models:/{args.model_name}@{args.alias}"
    model = mlflow.sklearn.load_model(model_uri)

    pdf = spark.table(source).toPandas()
    feature_rows = []
    meta = []
    for _, row in pdf.iterrows():
        d = row.to_dict()
        feats = row_to_features(d)
        feature_rows.append([feats[c] for c in FEATURE_COLUMNS])
        meta.append(
            {
                "customer_id": d.get("customer_id"),
                "region": d.get("region"),
            }
        )

    X = pd.DataFrame(feature_rows, columns=FEATURE_COLUMNS)
    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)
    scored_at = datetime.now(timezone.utc).isoformat()

    out = pd.DataFrame(meta)
    out["churn_probability"] = proba
    out["churn_prediction"] = pred
    out["model_name"] = args.model_name
    out["model_version"] = mv.version
    out["model_alias"] = args.alias
    out["scored_at"] = scored_at

    (
        spark.createDataFrame(out)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(target)
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "target": target,
                "n_scored": int(len(out)),
                "model_version": mv.version,
                "positive_rate": float(pred.mean()) if len(pred) else 0.0,
            }
        )
    )


if __name__ == "__main__":
    main()
