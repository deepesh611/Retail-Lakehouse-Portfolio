# 2-minute demo script

**Before recording:** restart the Databricks App if it auto-stopped (~24h). Ensure gold + predictions are fresh.

| Time | Action | Say |
|---|---|---|
| 0:00–0:20 | Show architecture diagram in README | “End-to-end retail lakehouse on Free Edition: ingest → Lakeflow → gold → churn ML → control-room App.” |
| 0:20–0:40 | Catalog Explorer lineage | “Auto Loader bronze to silver with quarantine, SCD2 customers, gold 360.” |
| 0:40–1:00 | Run / show Genie or dashboard | “Certified gold answers region revenue and churn rate.” |
| 1:00–1:25 | MLflow / aliases | “Champion/challenger in UC; promotion job gates on ROC-AUC and F1.” |
| 1:25–1:50 | Open App | “Control room: pipeline health, leaderboard, batch predictions lookup.” |
| 1:50–2:00 | Close | “Repo + DAB + CI are the durable portfolio; Free Edition workarounds documented.” |

## Cold-start commands

```bash
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run synthetic_ingest -t dev
# Start pipeline refresh in UI or CLI, then:
databricks bundle run apply_governance -t dev
databricks bundle run ml_train_promote_score -t dev
# Start App from workspace; optional:
databricks bundle run anomaly_monitor -t dev
```
