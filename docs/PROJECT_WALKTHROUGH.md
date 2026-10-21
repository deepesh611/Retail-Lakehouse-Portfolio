# Project walkthrough

What we built, how it was deployed on Databricks Free Edition, what broke, and how each break was fixed. Workspace: `https://dbc-2eeeec2a-2484.cloud.databricks.com`. Dev Unity Catalog schema: `workspace.dev_deepeshvcd6273_retail_dev` (Declarative Automation Bundles prefixes names in `development` mode).

The question the project answers: **which customers will churn, and is the pipeline healthy?**

## 1. What is in the repo

| Piece | Where | What it does |
|---|---|---|
| Bundle | `databricks.yml` | `dev` and `prod` targets, paused schedules, serverless-only |
| Landing | `src/ingest/generate_synthetic.py` | Synthetic customers, orders, clickstream into a UC Volume |
| Lakehouse | `src/pipelines/bronze_silver_gold.py` | Auto Loader bronze, expectations + quarantine, SCD Type 2, gold 360 |
| Governance | `src/pipelines/governance.sql` | PII tags, email mask, region view |
| ML | `src/ml/train.py`, `promote.py`, `batch_score.py` | CPU gradient boosting, champion/challenger, Delta predictions |
| App | `src/app/` | Streamlit control room + FastAPI over the same services |
| Monitor | `src/monitor/anomaly_monitor.py` | `availableNow` stream, not a continuous stream |
| CI | `.github/workflows/ci.yml` | pytest; `bundle validate` / deploy when secrets exist |
| Tests | `tests/` | Offline checks (11 passing) |

Delivery is `databricks bundle deploy -t dev`, then `databricks bundle run <resource> -t dev`.

## 2. How the data moves

1. Job `synthetic_ingest` writes JSON under `/Volumes/workspace/dev_deepeshvcd6273_retail_dev/raw_landing/{customers,orders,clickstream}/ingest_date=...`.
2. Lakeflow pipeline `a2cd9445-7256-4ff3-874e-3ac0099a06b2` (`[dev deepeshvcd6273] retail-lakehouse-pipeline-dev`) loads those files with Auto Loader.
3. Silver drops bad orders into `silver_orders_quarantine` (1,028 rows on the first load) and keeps valid orders, customers, and clicks.
4. Gold builds `gold_customers_scd2`, `gold_order_facts`, `gold_customer_360`, and `gold_region_kpis`.
5. Churn label uses the **latest order date in the data** as “today”, not the wall-clock date. Otherwise almost every customer looked churned.
6. Job `ml_train_promote_score` trains, compares challenger to champion, and writes `churn_predictions`.
7. The App reads the registry, predictions, pipeline state, and Genie.

Verified counts from the first successful path:

- Ingest: 5,000 customers, 50,000 orders, 80,000 click events
- Gold customers: 5,000, churn rate about 49.2%
- Model v1: accuracy 0.90, F1 0.89, ROC AUC 0.90, promoted to `champion`
- Batch score: 5,000 rows, average probability about 0.491

## 3. What we ran on the workspace

CLI profile `my-workspace` (Databricks CLI v1.21). Commands, in the order that mattered:

```bash
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run synthetic_ingest -t dev
databricks bundle run retail_lakehouse -t dev --full-refresh-all
databricks bundle run apply_governance -t dev
databricks bundle run ml_train_promote_score -t dev
databricks apps deploy retail-churn-control-room-dev --source-code-path <bundle app path>
databricks bundle run anomaly_monitor -t dev
```

SQL checks used the statement execution API against warehouse `2e7d08a047a927cf` (`Serverless Starter Warehouse`, 2X-Small).

You built the AI/BI dashboard and the Genie space in the UI. Genie space id `01f1cd36583b1d4ea63bf88d4f0508d6` is now in the App env. A direct Genie call (“Which region has the highest revenue?”) answered **central, about $1,558,692**.

App URL: https://retail-churn-control-room-dev-7474644751098620.aws.databricksapps.com

## 4. Problems and fixes

**UC Volume writes.** The first ingest used `pathlib.mkdir` on `/Volumes/...` and failed with `OSError: [Errno 95] Operation not supported`. Landing files are now written with Spark `DataFrame.write.json`.

**Development name prefix.** `mode: development` created schema `dev_deepeshvcd6273_retail_dev`, while jobs still passed `retail_dev`. Job and pipeline parameters now use `${resources.schemas.retail_schema.name}`, and the raw path is built from that name.

**Governance script.** `spark_python_task` runs the file with `exec`, so `__file__` does not exist. The job passes `--sql-file` from `${workspace.file_path}/src/pipelines/governance.sql`.

**Churn labels.** Comparing last order to `current_date()` labeled about 99% of customers churned, because synthetic orders stop in 2025. Gold now measures recency from the max order date in the table.

**Training NaNs.** `value or 0` does not replace pandas `NaN`. Feature building uses an explicit finite-float conversion, and training fills remaining nulls.

**App could not see the pipeline.** The App runs as service principal `app-2snpls retail-churn-control-room-dev`, which was not on the pipeline ACL. It now has `CAN_VIEW`. The App also stores the real pipeline id, because the live name is prefixed with `[dev deepeshvcd6273]`.

**Empty late-events folder.** Auto Loader raised `CF_EMPTY_DIR_FOR_SCHEMA_INFERENCE`. The monitor now sets the schema itself and, if the folder is empty, writes two demo events before `availableNow`. Resulting alerts: `LATE0001` high amount 2500, `LATE0002` negative amount -15.

**SCD2 updates were dropped.** `dropDuplicates(["customer_id"])` on the silver stream kept the first version forever. That dedupe was removed. A `change_ts` hint orders versions. The first incremental update failed with `STREAMING_STATEFUL_OPERATOR_NOT_MATCH_IN_STATE_METADATA` because the old checkpoint still expected the dedupe operator. A full refresh of `silver_customers`, `gold_customers_scd2`, and `gold_customer_360` cleared that. Afterward `C000001` has two rows: `gold` closed at `2026-10-22T00:00:00Z`, and current `platinum` with `__END_AT` null.

**Genie from the App.** The space id was only in a local `.env`. It is now `RETAIL_GENIE_SPACE_ID` in `src/app/app.yaml`, and the App principal has `CAN_RUN` on the space. `.env` stays gitignored and is not the deploy source.

## 5. Checks that passed on 21 Oct 2026

- `pytest`: 11 passed
- `databricks bundle validate -t dev`: OK
- Ingest job: terminated success
- Pipeline full refresh: completed; bronze, silver, quarantine, and gold tables exist
- Governance: masked email `cu***@example.com`; region view returns only `north`
- Column tags on `gold_customer_360`: `email` pii/email and sensitivity/high; `full_name` pii/name and sensitivity/medium
- Second pipeline update: customer flows full-refreshed after the checkpoint error; SCD2 history verified
- ML train, promote (`thresholds_passed`), batch score: success
- Anomaly monitor: success, two alert rows
- App deploy: `SUCCEEDED` and running
- Genie API: answered from `gold_region_kpis`
- Dashboard and App tab click-through: confirmed by you in the UI

## 6. Left on purpose

- **Second full model retrain.** The first run already registered v1 and scored 5,000 customers. Another train would spend Free Edition quota without a new gate.
- **Demo video.** Script is in `docs/DEMO_SCRIPT.md`. The repo cannot record it.
- **CPU model serving.** `enable_serving` stays false. Live scores are the Delta lookup. An example endpoint file is `resources/serving/churn_endpoint.yml.example`.
- **`prod` target.** Defined and schedules paused. Not deployed; Free Edition is a single workspace and `dev` is the running copy.

## 7. How to repeat a demo

```bash
databricks bundle deploy -t dev
databricks bundle run synthetic_ingest -t dev
databricks bundle run retail_lakehouse -t dev --refresh-all
databricks bundle run apply_governance -t dev
databricks bundle run ml_train_promote_score -t dev
databricks apps start retail-churn-control-room-dev
```

Free Edition stops the App about 24 hours after start. Restart it before showing the control room. If you change silver customer logic again, full-refresh `silver_customers` so the streaming checkpoint does not keep the old dedupe state.
