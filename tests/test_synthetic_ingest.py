from __future__ import annotations

import json
from pathlib import Path

from src.ingest.generate_synthetic import (
    build_clickstream,
    build_customers,
    build_orders,
    volume_root,
    write_dataset,
)
import random


def test_volume_root():
    assert volume_root("workspace", "retail_dev", "raw_landing") == (
        "/Volumes/workspace/retail_dev/raw_landing"
    )


def test_build_and_write(tmp_path: Path):
    rng = random.Random(0)
    customers = build_customers(50, rng)
    orders = build_orders(200, customers, rng, bad_row_rate=0.05)
    events = build_clickstream(100, customers, rng)
    counts = write_dataset(tmp_path, "2026-10-16", customers, orders, events)
    assert counts["customers"] == 50
    assert counts["orders"] == 200
    assert counts["clickstream"] == 100
    order_file = next((tmp_path / "orders").rglob("*.json"))
    lines = order_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 200
    # At least one intentional bad row expected with 5% rate over 200 rows
    parsed = [json.loads(x) for x in lines]
    bad = [
        o
        for o in parsed
        if o["order_id"] is None or o["amount"] < 0 or o["region"] == "INVALID"
    ]
    assert len(bad) >= 1
