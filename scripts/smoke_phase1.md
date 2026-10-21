# Phase 1 smoke (run twice before Phase 2)

**Dev schema:** DAB prefixes schemas in development mode. Example:
`workspace.dev_<shortuser>_retail_dev` (resolve via `databricks schemas list workspace`).

```bash
databricks bundle deploy -t dev
databricks bundle run synthetic_ingest -t dev
databricks bundle run retail_lakehouse -t dev --full-refresh-all
databricks bundle run apply_governance -t dev
```

1. Confirm tables: `bronze_*`, `silver_*`, `silver_orders_quarantine`, `gold_*`.
2. SQL (replace schema if needed):

```sql
SELECT COUNT(*) FROM workspace.dev_deepeshvcd6273_retail_dev.silver_orders_quarantine;
SELECT email FROM workspace.dev_deepeshvcd6273_retail_dev.gold_customer_360_masked LIMIT 5;
SELECT DISTINCT region FROM workspace.dev_deepeshvcd6273_retail_dev.gold_customer_360_region_north;
SELECT COUNT(*), SUM(churn_label) FROM workspace.dev_deepeshvcd6273_retail_dev.gold_customer_360;
```

3. Build dashboard + Genie per docs/DASHBOARD.md and docs/GENIE.md (gold tables only).
4. Tick Phase 1E in docs/QUALITY_GATES.md after smoke #1 and #2.
