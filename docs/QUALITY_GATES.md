# Quality gates checklist

Rule: after each checkpoint — **Works → Issues → Inefficiencies → Fix → only then proceed**.

**Dev schema note:** DAB `mode: development` prefixes UC schemas. On this workspace the live schema is `workspace.dev_deepeshvcd6273_retail_dev` (not bare `retail_dev`). Jobs/pipeline now resolve `${resources.schemas.retail_schema.name}` automatically.

**Workspace smoke progress (2026-10-21):** Phase 0–2 verified. App click-through and Genie/dashboard confirmed in the workspace UI.

## Phase 0

- [x] Databricks Free Edition workspace available; LinkedIn verify if offered
- [x] Databricks CLI ≥ 0.218 authenticated (`databricks auth login` or profile)
- [x] `databricks bundle validate -t dev` passes
- [x] Quotas noted: 1× 2X-Small warehouse, ≤5 concurrent job tasks, 1 active pipeline/type, ≤3 apps (24h stop)

## Phase 1A — Ingest

- [x] `databricks bundle deploy -t dev`
- [x] `databricks bundle run synthetic_ingest -t dev` succeeds
- [x] Files under `/Volumes/workspace/dev_deepeshvcd6273_retail_dev/raw_landing/{customers,orders,clickstream}/...`
- [x] Counts match job parameters (5k / 50k / 80k); no secrets in logs
- [x] Inefficiency scan: data size small enough; single task; serverless env
- [x] Fixed: Spark Volume writes (pathlib mkdir fails on UC Volumes)

## Phase 1B — Pipeline

- [x] Full refresh of `retail_lakehouse` pipeline succeeds
- [ ] Incremental refresh succeeds (optional second run)
- [x] Quarantine table has bad rows (`silver_orders_quarantine` = 1028)
- [ ] SCD2: update a customer → history closed, new current row (manual Catalog check)
- [x] Lineage tables present: bronze_*, silver_*, gold_*
- [x] Inefficiency scan: serverless true; no always-on clusters
- [x] Fixed: churn `as_of` anchored to max order date (wall-clock “today” labeled ~all churned)

## Phase 1C — Governance

- [x] `databricks bundle run apply_governance -t dev`
- [x] `gold_customer_360_masked` shows masked emails (`cu***@example.com`)
- [x] `gold_customer_360_region_north` filters to north
- [ ] Tags visible in Catalog Explorer (UI check)
- [x] Fixed: `__file__` missing under spark_python_task — pass `--sql-file` via bundle

## Phase 1D — BI / Genie

- [x] Gold SQL queries load on 2X-Small warehouse (API-verified)
- [x] Genie space answers 3 scripted questions (see `docs/GENIE.md`)
- [x] AI/BI dashboard tiles (see `docs/DASHBOARD.md`)

## Phase 1E — Exit

- [x] Smoke #1: ingest → pipeline → gold query → governance
- [x] Genie + dashboard confirmed in UI
- [ ] Smoke #2 (repeat full ingest → pipeline)
- [x] Offline CI pieces: `pytest` 11 passed; `bundle validate` OK

## Phase 2A — Train

- [x] `databricks bundle run ml_train_promote_score -t dev`
- [x] Experiment run + UC model v1 + metrics (roc_auc≈0.90, f1≈0.89)
- [x] `challenger` / `champion` aliases set
- [x] Fixed: NaN coercion in feature builder

## Phase 2B — Promote + batch score

- [x] Promote wrote audit (`promoted: true`, thresholds_passed)
- [x] `churn_predictions` = 5000 rows (avg prob ≈ 0.491)

## Phase 2C — Serving

- [x] Documented Delta fallback (`enable_serving=false`); batch path is primary

## Phase 2D — App

- [x] App resource deployed: `retail-churn-control-room-dev`
- [x] App source deployed + started (`databricks apps deploy ...` → SUCCEEDED)
- [x] URL: https://retail-churn-control-room-dev-7474644751098620.aws.databricksapps.com
- [x] Clicked through Streamlit tabs (registry / predictions / pipeline health)
- [x] No PAT in source

## Phase 2E — Exit

- [x] Smoke: train → promote → score → App started
- [x] Click-through App UI
- [ ] Optional second ML smoke

## Phase 3

- [ ] Genie-in-App with `RETAIL_GENIE_SPACE_ID`
- [ ] Optional `anomaly_monitor` availableNow run
- [ ] README / architecture / demo video cold-start works
