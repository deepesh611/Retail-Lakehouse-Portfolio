"""Light incremental monitor using Structured Streaming availableNow trigger.

Processes synthetic late-arriving order events and flags anomalies into a gold
alert table. Continuous triggers are not used (Free Edition / serverless).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--volume-name", default="raw_landing")
    p.add_argument("--relative-path", default="late_events")
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--amount-threshold", type=float, default=1000.0)
    return p.parse_args()


LATE_EVENT_SCHEMA_FIELDS = (
    ("order_id", "string"),
    ("customer_id", "string"),
    ("amount", "double"),
    ("region", "string"),
)


def _event_schema():
    from pyspark.sql.types import DoubleType, StringType, StructField, StructType

    types = {"string": StringType(), "double": DoubleType()}
    return StructType(
        [StructField(name, types[kind], True) for name, kind in LATE_EVENT_SCHEMA_FIELDS]
    )


def _has_data_files(spark, path: str) -> bool:
    try:
        from pyspark.dbutils import DBUtils

        entries = DBUtils(spark).fs.ls(path)
    except Exception:
        return False
    return any(not item.name.startswith("_") and not item.isDir() for item in entries)


def _seed_if_empty(spark, path: str) -> bool:
    """Write two demo anomalies when the landing path has no files.

    Auto Loader cannot infer a schema from an empty directory.
    """
    if _has_data_files(spark, path):
        return False
    rows = [
        ("LATE0001", "C000001", 2500.0, "north"),
        ("LATE0002", "C000002", -15.0, "west"),
    ]
    spark.createDataFrame(rows, schema=_event_schema()).coalesce(1).write.mode(
        "append"
    ).json(path)
    return True


def main() -> None:
    args = _parse_args()
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    spark = SparkSession.builder.getOrCreate()
    source = (
        f"/Volumes/{args.catalog}/{args.schema}/{args.volume_name}/"
        f"{args.relative_path}"
    )
    checkpoint = args.checkpoint or (
        f"/Volumes/{args.catalog}/{args.schema}/{args.volume_name}/"
        f"_checkpoints/anomaly_monitor"
    )
    target = f"{args.catalog}.{args.schema}.gold_anomaly_alerts"

    seeded = _seed_if_empty(spark, source)

    stream_df = (
        spark.readStream.format("cloudFiles")
        .schema(_event_schema())
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"{checkpoint}/schema")
        .load(source)
    )

    anomalies = (
        stream_df.withColumn("detected_at", F.lit(datetime.now(timezone.utc).isoformat()))
        .withColumn(
            "anomaly_type",
            F.when(F.col("amount") > args.amount_threshold, F.lit("high_amount"))
            .when(F.col("amount") < 0, F.lit("negative_amount"))
            .otherwise(F.lit("none")),
        )
        .filter(F.col("anomaly_type") != "none")
        .select(
            "order_id",
            "customer_id",
            "amount",
            "region",
            "anomaly_type",
            "detected_at",
        )
    )

    query = (
        anomalies.writeStream.format("delta")
        .option("checkpointLocation", checkpoint)
        .outputMode("append")
        .trigger(availableNow=True)
        .toTable(target)
    )
    query.awaitTermination()

    print(
        json.dumps(
            {
                "status": "ok",
                "source": source,
                "target": target,
                "trigger": "availableNow",
                "seeded_demo_events": seeded,
            }
        )
    )


if __name__ == "__main__":
    main()
