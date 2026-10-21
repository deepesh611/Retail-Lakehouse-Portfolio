"""Offline sanity check that Phase 0+ scaffold files exist (no Databricks auth)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "databricks.yml",
    "resources/schemas.yml",
    "resources/jobs/ingest_job.yml",
    "resources/jobs/governance_job.yml",
    "resources/jobs/ml_jobs.yml",
    "resources/jobs/monitor_job.yml",
    "resources/pipelines/retail_pipeline.yml",
    "resources/apps/control_room.yml",
    "resources/experiments.yml",
    "src/ingest/generate_synthetic.py",
    "src/pipelines/bronze_silver_gold.py",
    "src/pipelines/governance.sql",
    "src/pipelines/apply_governance.py",
    "src/ml/features.py",
    "src/ml/train.py",
    "src/ml/promote.py",
    "src/ml/batch_score.py",
    "src/app/api.py",
    "src/app/services.py",
    "src/app/streamlit_app.py",
    "src/app/app.yaml",
    "src/monitor/anomaly_monitor.py",
    "docs/QUALITY_GATES.md",
    "docs/FREE_EDITION.md",
    "docs/ARCHITECTURE.md",
    "docs/GENIE.md",
    "docs/DASHBOARD.md",
    "docs/DEMO_SCRIPT.md",
    ".github/workflows/ci.yml",
]


def main() -> int:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        print("MISSING:")
        for m in missing:
            print(f"  - {m}")
        return 1
    print(f"OK: {len(REQUIRED)} required paths present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
