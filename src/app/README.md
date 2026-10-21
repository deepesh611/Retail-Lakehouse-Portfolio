# Churn control room App

- `streamlit_app.py` — UI (Databricks Apps entry via `app.yaml`)
- `api.py` — FastAPI HTTP surface for MLflow / predictions / Genie
- `services.py` — shared Databricks SDK + MLflow logic (no hardcoded tokens)
- `config.py` — env-driven settings

Apps on Free Edition stop after ~24 hours; restart before demos.
