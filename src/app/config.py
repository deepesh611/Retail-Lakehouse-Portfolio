"""App configuration from environment (set by Databricks Apps / app.yaml)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    catalog: str
    schema: str
    model_name: str
    experiment_name: str
    serving_endpoint: str
    pipeline_name: str
    pipeline_id: str | None
    enable_serving: bool
    genie_space_id: str | None
    host: str | None

    @property
    def predictions_table(self) -> str:
        return f"{self.catalog}.{self.schema}.churn_predictions"

    @property
    def customer_table(self) -> str:
        return f"{self.catalog}.{self.schema}.gold_customer_360"

    @property
    def audit_table(self) -> str:
        return f"{self.catalog}.{self.schema}.ml_promotion_audit"


def get_settings() -> Settings:
    return Settings(
        catalog=os.getenv("RETAIL_CATALOG", "workspace"),
        schema=os.getenv("RETAIL_SCHEMA", "retail_dev"),
        model_name=os.getenv(
            "RETAIL_MODEL_NAME", "workspace.retail_dev.churn_model"
        ),
        experiment_name=os.getenv("RETAIL_EXPERIMENT_NAME", "/Shared/retail-churn-dev"),
        serving_endpoint=os.getenv(
            "RETAIL_SERVING_ENDPOINT", "retail-churn-endpoint-dev"
        ),
        pipeline_name=os.getenv(
            "RETAIL_PIPELINE_NAME", "retail-lakehouse-pipeline-dev"
        ),
        pipeline_id=os.getenv("RETAIL_PIPELINE_ID") or None,
        enable_serving=os.getenv("RETAIL_ENABLE_SERVING", "false").lower()
        in {"1", "true", "yes"},
        genie_space_id=os.getenv("RETAIL_GENIE_SPACE_ID") or None,
        host=os.getenv("DATABRICKS_HOST") or None,
    )
