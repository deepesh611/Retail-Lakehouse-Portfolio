# Phase 0 setup checklist

1. Create a [Databricks Free Edition](https://www.databricks.com/learn/free-edition) workspace.
2. Complete **Verify identity** (LinkedIn) if shown.
3. Install CLI ≥ 0.218: https://docs.databricks.com/dev-tools/cli/install.html
4. Authenticate:
   ```bash
   databricks auth login
   # or configure a profile in ~/.databrickscfg
   ```
5. From repo root:
   ```bash
   pip install -r requirements-dev.txt
   pytest -q
   databricks bundle validate -t dev
   ```
6. Confirm workspace features: Jobs, Lakeflow Pipelines, Volumes, Apps, MLflow, Genie.
7. Tick Phase 0 in `docs/QUALITY_GATES.md`, then start Phase 1A.
