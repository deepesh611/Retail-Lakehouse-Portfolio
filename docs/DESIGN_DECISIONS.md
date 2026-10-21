# Design decisions

1. **One business question** — churn risk + pipeline health — keeps Genie, dashboard, ML, and App coherent.
2. **Synthetic retail data** — non-commercial Free Edition; injectable bad rows for expectations.
3. **Lakeflow Declarative Pipeline** — Auto Loader, expectations, quarantine, `apply_changes` SCD2.
4. **Governance as views + UDF** — Free Edition is single-user without SSO; still demonstrates mask/filter patterns.
5. **GradientBoostingClassifier (CPU)** — small, serveable, no GPU dependency.
6. **Batch inference primary** — serving endpoint is optional; App falls back to Delta.
7. **DAB `dev`/`prod` + paused triggers** — platform engineering signal without burning quota.
8. **Streamlit App + FastAPI services** — UI for demos; HTTP API for the “expose MLflow via API” story.
9. **Genie before RAG** — ask-your-data without AI Search quota risk; RAG explicitly out of scope until Genie works.
10. **Honesty about limits** — `docs/FREE_EDITION.md` is part of the portfolio, not an apology.
