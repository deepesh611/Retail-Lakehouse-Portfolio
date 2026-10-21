"""Seed a few anomalous late events into the Volume for the availableNow monitor."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", default="workspace")
    p.add_argument("--schema", default="retail_dev")
    p.add_argument("--volume-name", default="raw_landing")
    p.add_argument("--local-out", default=None)
    args = p.parse_args()

    base = (
        Path(args.local_out)
        if args.local_out
        else Path(f"/Volumes/{args.catalog}/{args.schema}/{args.volume_name}")
    )
    out = base / "late_events" / f"part-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
    rows = [
        {
            "order_id": "LATE0001",
            "customer_id": "C000001",
            "amount": 2500.0,
            "region": "north",
        },
        {
            "order_id": "LATE0002",
            "customer_id": "C000002",
            "amount": -15.0,
            "region": "west",
        },
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print({"wrote": str(out), "n": len(rows)})


if __name__ == "__main__":
    main()
