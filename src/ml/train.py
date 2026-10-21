"""Train a CPU churn classifier, log to MLflow, register in Unity Catalog."""

from __future__ import annotations

import argparse
import json
from typing import Any

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.models.signature import infer_signature
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from features import FEATURE_COLUMNS, LABEL_COLUMN, row_to_features


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--experiment-name", required=True)
    p.add_argument("--model-name", required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--alias", default="challenger", choices=["challenger", "champion"])
    p.add_argument(
        "--source-table",
        default="gold_customer_360",
        help="Fully qualified or schema-relative gold table",
    )
    return p.parse_args()


def load_feature_frame(spark, table: str) -> pd.DataFrame:
    pdf = spark.table(table).toPandas()
    records = []
    for _, row in pdf.iterrows():
        feats = row_to_features(row.to_dict())
        feats[LABEL_COLUMN] = int(row.get(LABEL_COLUMN) or 0)
        feats["customer_id"] = row.get("customer_id")
        records.append(feats)
    return pd.DataFrame.from_records(records)


def train_and_log(
    df: pd.DataFrame,
    experiment_name: str,
    model_name: str,
    seed: int,
    alias: str,
) -> dict[str, Any]:
    mlflow.set_experiment(experiment_name)
    X = df[FEATURE_COLUMNS].fillna(0.0)
    y = df[LABEL_COLUMN].fillna(0).astype(int)
    # Extreme class imbalance is possible with synthetic labels; stratify only if both classes exist
    stratify = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=seed, stratify=stratify
    )

    model = GradientBoostingClassifier(
        random_state=seed,
        n_estimators=80,
        max_depth=3,
        learning_rate=0.08,
    )

    with mlflow.start_run(run_name="churn-gbm") as run:
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)

        metrics = {
            "accuracy": float(accuracy_score(y_test, pred)),
            "precision": float(precision_score(y_test, pred, zero_division=0)),
            "recall": float(recall_score(y_test, pred, zero_division=0)),
            "f1": float(f1_score(y_test, pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, proba))
            if y_test.nunique() > 1
            else 0.0,
        }
        params = {
            "model_type": "GradientBoostingClassifier",
            "n_estimators": 80,
            "max_depth": 3,
            "learning_rate": 0.08,
            "seed": seed,
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
        }
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)

        signature = infer_signature(X_train, model.predict_proba(X_train)[:, 1])
        input_example = X_train.head(3)

        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            signature=signature,
            input_example=input_example,
            registered_model_name=model_name,
        )

        client = mlflow.tracking.MlflowClient()
        versions = client.search_model_versions(f"name='{model_name}'")
        latest = max(versions, key=lambda v: int(v.version))
        client.set_registered_model_alias(model_name, alias, latest.version)
        # Bootstrap champion on first successful train if missing
        try:
            client.get_model_version_by_alias(model_name, "champion")
        except Exception:
            client.set_registered_model_alias(model_name, "champion", latest.version)

        result = {
            "run_id": run.info.run_id,
            "model_name": model_name,
            "version": latest.version,
            "alias": alias,
            "metrics": metrics,
        }
        print(json.dumps(result))
        return result


def main() -> None:
    args = _parse_args()
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    table = args.source_table
    if table.count(".") == 0:
        table = f"{args.catalog}.{args.schema}.{table}"

    df = load_feature_frame(spark, table)
    if df.empty:
        raise SystemExit("No feature rows found — run the lakehouse pipeline first.")
    # Free Edition comfort: downsample if huge
    if len(df) > 20000:
        df = df.sample(n=20000, random_state=args.seed)

    train_and_log(
        df,
        experiment_name=args.experiment_name,
        model_name=args.model_name,
        seed=args.seed,
        alias=args.alias,
    )


if __name__ == "__main__":
    main()
