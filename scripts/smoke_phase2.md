# Phase 2 smoke (run twice before Phase 3)

```bash
databricks bundle run ml_train_promote_score -t dev
databricks apps start retail-churn-control-room-dev
```

1. MLflow experiment (name is development-prefixed under `/Shared/...`) has a run with metrics + signature.
2. UC model `workspace.dev_<user>_retail_dev.churn_model` has `champion` / `challenger`.
3. Table `...churn_predictions` has rows.
4. Table `...ml_promotion_audit` has a decision row.
5. Open App → pipeline health, leaderboard, predictions, score `C000001`.
6. Confirm no PATs in repo; App uses workspace identity / app SP.
