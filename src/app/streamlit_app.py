"""Streamlit control room UI — uses services.py directly (Databricks Apps friendly)."""

from __future__ import annotations

import streamlit as st

from config import get_settings
from services import (
    genie_ask,
    get_experiment_runs,
    get_model_info,
    get_predictions,
    pipeline_health,
    predict_customer,
)

st.set_page_config(page_title="Retail Churn Control Room", layout="wide")
st.title("Retail Churn Control Room")
st.caption("Which customers will churn next week, and is the pipeline healthy?")

settings = get_settings()
with st.sidebar:
    st.markdown("### Config")
    st.code(
        f"catalog={settings.catalog}\n"
        f"schema={settings.schema}\n"
        f"model={settings.model_name}\n"
        f"pipeline={settings.pipeline_name}\n"
        f"serving={settings.enable_serving}",
        language="text",
    )
    st.info("Apps auto-stop after ~24h on Free Edition — restart before demos.")

tabs = st.tabs(
    ["Pipeline health", "Model leaderboard", "Predictions", "Score customer", "Ask Genie"]
)

with tabs[0]:
    st.subheader("Lakeflow pipeline health")
    if st.button("Refresh pipeline status", key="pipe"):
        try:
            st.json(pipeline_health(settings))
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

with tabs[1]:
    st.subheader("Registered model + experiment runs")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Load model registry", key="model"):
            try:
                st.json(get_model_info(settings))
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
    with col2:
        if st.button("Load run leaderboard", key="runs"):
            try:
                st.json(get_experiment_runs(settings, limit=15))
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

SAMPLE_CUSTOMER_IDS = ("C004323", "C004464", "C001757", "C000001")

with tabs[2]:
    st.subheader("Latest batch churn predictions")
    st.caption(f"Source: `{settings.predictions_table}` (top churn probability).")
    limit = st.slider("Rows", 10, 100, 25)
    if st.button("Load predictions", key="preds"):
        try:
            data = get_predictions(settings, limit=limit)
            rows = data.get("rows") or []
            if rows:
                st.dataframe(rows, use_container_width=True)
            else:
                st.info("No prediction rows yet — run the batch score job.")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

with tabs[3]:
    st.subheader("Look up batch score for a customer")
    st.caption(
        "Try a high-risk sample: "
        + ", ".join(f"`{cid}`" for cid in SAMPLE_CUSTOMER_IDS[:3])
        + " (or any `C000001`–`C005000`)."
    )
    customer_id = st.text_input("customer_id", value=SAMPLE_CUSTOMER_IDS[0])
    if st.button("Predict / lookup", key="predict"):
        try:
            st.json(predict_customer(customer_id.strip(), settings))
        except LookupError as exc:
            st.error(
                f"{exc}. Use a sample id like `{SAMPLE_CUSTOMER_IDS[0]}` "
                "or load predictions first and copy a customer_id."
            )
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

with tabs[4]:
    st.subheader("Ask your gold data (Genie)")
    starters = [
        "Which region has the highest revenue?",
        "How many customers have churn_label = 1?",
        "What is the average order value by loyalty tier?",
    ]
    q = st.selectbox("Starter question", starters)
    custom = st.text_input("Or type your own question", value="")
    question = custom.strip() or q
    if st.button("Ask Genie", key="genie"):
        try:
            st.json(genie_ask(question))
        except Exception as exc:  # noqa: BLE001
            st.error(f"Genie failed: {exc}")
