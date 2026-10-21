"""Generate synthetic retail landing files into a Unity Catalog Volume.

Designed for Databricks Free Edition: small defaults, idempotent by ingest_date,
no external network calls, no secrets.

Volume writes use Spark (UC Volumes do not support pathlib.mkdir on parent paths).
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

REGIONS = ["north", "south", "east", "west", "central"]
CHANNELS = ["web", "mobile", "store", "partner"]
EVENT_TYPES = ["page_view", "add_to_cart", "checkout_start", "purchase", "search"]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthetic retail ingest")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--volume-name", required=True)
    parser.add_argument("--n-customers", type=int, default=5000)
    parser.add_argument("--n-orders", type=int, default=50000)
    parser.add_argument("--n-events", type=int, default=80000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--ingest-date",
        default=None,
        help="Partition date YYYY-MM-DD (default: today UTC)",
    )
    parser.add_argument(
        "--bad-row-rate",
        type=float,
        default=0.02,
        help="Fraction of orders with intentional quality issues",
    )
    parser.add_argument(
        "--local-out",
        default=None,
        help="Optional local directory for offline tests (skips Volume write)",
    )
    return parser.parse_args()


def volume_root(catalog: str, schema: str, volume_name: str) -> str:
    return f"/Volumes/{catalog}/{schema}/{volume_name}"


def build_customers(n: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(1, n + 1):
        region = rng.choice(REGIONS)
        signup = date(2022, 1, 1) + timedelta(days=rng.randint(0, 900))
        rows.append(
            {
                "customer_id": f"C{i:06d}",
                "email": f"customer{i}@example.com",
                "full_name": f"Customer {i}",
                "region": region,
                "signup_date": signup.isoformat(),
                "loyalty_tier": rng.choice(["bronze", "silver", "gold", "platinum"]),
                "is_active": rng.random() > 0.15,
            }
        )
    return rows


def build_orders(
    n: int,
    customers: list[dict[str, Any]],
    rng: random.Random,
    bad_row_rate: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(1, n + 1):
        cust = rng.choice(customers)
        order_ts = datetime(2024, 1, 1) + timedelta(
            days=rng.randint(0, 600), hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
        )
        amount = round(rng.uniform(5.0, 500.0), 2)
        order_id: str | None = f"O{i:08d}"
        if rng.random() < bad_row_rate:
            kind = rng.choice(["null_id", "neg_amount", "bad_region"])
            if kind == "null_id":
                order_id = None
            elif kind == "neg_amount":
                amount = -abs(amount)
            else:
                cust = {**cust, "region": "INVALID"}

        rows.append(
            {
                "order_id": order_id,
                "customer_id": cust["customer_id"],
                "order_ts": order_ts.isoformat(sep=" "),
                "amount": amount,
                "channel": rng.choice(CHANNELS),
                "region": cust["region"],
                "status": rng.choice(
                    ["completed", "completed", "completed", "cancelled", "returned"]
                ),
            }
        )
    return rows


def build_clickstream(
    n: int,
    customers: list[dict[str, Any]],
    rng: random.Random,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(1, n + 1):
        cust = rng.choice(customers)
        event_ts = datetime(2024, 1, 1) + timedelta(
            days=rng.randint(0, 600), hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
        )
        rows.append(
            {
                "event_id": f"E{i:09d}",
                "customer_id": cust["customer_id"],
                "event_ts": event_ts.isoformat(sep=" "),
                "event_type": rng.choice(EVENT_TYPES),
                "session_id": f"S{rng.randint(1, max(n // 2, 1)):08d}",
                "page": rng.choice(["home", "pdp", "cart", "checkout", "search"]),
            }
        )
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    """Local filesystem write (unit tests / --local-out)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")
    return len(rows)


def write_dataset_local(
    base: Path,
    ingest_date: str,
    customers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, int]:
    counts = {
        "customers": write_jsonl(
            base / "customers" / f"ingest_date={ingest_date}" / "part-0000.json",
            customers,
        ),
        "orders": write_jsonl(
            base / "orders" / f"ingest_date={ingest_date}" / "part-0000.json",
            orders,
        ),
        "clickstream": write_jsonl(
            base / "clickstream" / f"ingest_date={ingest_date}" / "part-0000.json",
            events,
        ),
    }
    manifest = {
        "ingest_date": ingest_date,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "counts": counts,
    }
    manifest_path = base / "_manifests" / f"ingest_date={ingest_date}" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return counts


def write_dataset_volume(
    base: str,
    ingest_date: str,
    customers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, int]:
    """Write JSON datasets to a UC Volume via Spark (reliable on serverless)."""
    from pyspark.sql import SparkSession
    from pyspark.sql.types import (
        BooleanType,
        DoubleType,
        StringType,
        StructField,
        StructType,
    )

    spark = SparkSession.builder.getOrCreate()

    customer_schema = StructType(
        [
            StructField("customer_id", StringType(), False),
            StructField("email", StringType(), True),
            StructField("full_name", StringType(), True),
            StructField("region", StringType(), True),
            StructField("signup_date", StringType(), True),
            StructField("loyalty_tier", StringType(), True),
            StructField("is_active", BooleanType(), True),
        ]
    )
    order_schema = StructType(
        [
            StructField("order_id", StringType(), True),
            StructField("customer_id", StringType(), True),
            StructField("order_ts", StringType(), True),
            StructField("amount", DoubleType(), True),
            StructField("channel", StringType(), True),
            StructField("region", StringType(), True),
            StructField("status", StringType(), True),
        ]
    )
    event_schema = StructType(
        [
            StructField("event_id", StringType(), False),
            StructField("customer_id", StringType(), True),
            StructField("event_ts", StringType(), True),
            StructField("event_type", StringType(), True),
            StructField("session_id", StringType(), True),
            StructField("page", StringType(), True),
        ]
    )

    datasets = [
        ("customers", customers, customer_schema),
        ("orders", orders, order_schema),
        ("clickstream", events, event_schema),
    ]
    counts: dict[str, int] = {}
    for name, rows, schema in datasets:
        path = f"{base.rstrip('/')}/{name}/ingest_date={ingest_date}"
        df = spark.createDataFrame(rows, schema=schema)
        df.coalesce(1).write.mode("overwrite").json(path)
        counts[name] = len(rows)

    manifest = {
        "ingest_date": ingest_date,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "counts": counts,
    }
    manifest_path = f"{base.rstrip('/')}/_manifests/ingest_date={ingest_date}"
    spark.createDataFrame([manifest]).coalesce(1).write.mode("overwrite").json(
        manifest_path
    )
    return counts


# Back-compat name used by older call sites / docs
def write_dataset(
    base: Path,
    ingest_date: str,
    customers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, int]:
    return write_dataset_local(base, ingest_date, customers, orders, events)


def main() -> None:
    args = _parse_args()
    rng = random.Random(args.seed)
    ingest_date = args.ingest_date or datetime.utcnow().strftime("%Y-%m-%d")

    n_customers = min(max(args.n_customers, 100), 20000)
    n_orders = min(max(args.n_orders, 100), 200000)
    n_events = min(max(args.n_events, 100), 200000)

    customers = build_customers(n_customers, rng)
    orders = build_orders(n_orders, customers, rng, args.bad_row_rate)
    events = build_clickstream(n_events, customers, rng)

    if args.local_out:
        base: str | Path = Path(args.local_out)
        counts = write_dataset_local(base, ingest_date, customers, orders, events)
    else:
        base = volume_root(args.catalog, args.schema, args.volume_name)
        counts = write_dataset_volume(base, ingest_date, customers, orders, events)

    print(
        json.dumps(
            {
                "status": "ok",
                "base": str(base),
                "ingest_date": ingest_date,
                "counts": counts,
            }
        )
    )


if __name__ == "__main__":
    main()
