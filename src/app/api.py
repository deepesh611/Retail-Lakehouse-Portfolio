"""FastAPI control-room API — thin HTTP layer over services.py."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from services import (
    genie_ask,
    get_experiment_runs,
    get_model_info,
    get_model_versions,
    get_predictions,
    pipeline_health,
    predict_customer,
    workspace_client,
)

app = FastAPI(
    title="Retail Churn Control Room API",
    version="0.1.0",
    description="Expose MLflow registry, runs, predictions, pipeline health, Genie.",
)


class PredictRequest(BaseModel):
    customer_id: str | None = None
    features: dict[str, float] | None = None


class GenieAskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    conversation_id: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


@app.get("/models")
def list_models() -> dict[str, Any]:
    try:
        return get_model_info()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/models/{name:path}/versions")
def model_versions(name: str) -> dict[str, Any]:
    try:
        return get_model_versions(name)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/experiments/runs")
def experiment_runs(limit: int = 20) -> dict[str, Any]:
    try:
        return get_experiment_runs(limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/experiments/{experiment_id}/runs")
def experiment_runs_by_id(experiment_id: str, limit: int = 20) -> dict[str, Any]:
    # Kept for plan compatibility; delegates to name-based leaderboard when possible.
    try:
        data = get_experiment_runs(limit=limit)
        data["requested_experiment_id"] = experiment_id
        return data
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/predictions")
def latest_predictions(limit: int = 50) -> dict[str, Any]:
    try:
        return get_predictions(limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/predict")
def predict(body: PredictRequest) -> dict[str, Any]:
    settings = get_settings()
    if body.customer_id:
        try:
            return predict_customer(body.customer_id, settings)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not settings.enable_serving:
        raise HTTPException(
            status_code=501,
            detail=(
                "Live serving disabled on Free Edition. "
                "Pass customer_id to look up batch predictions, "
                "or set RETAIL_ENABLE_SERVING=true when an endpoint exists."
            ),
        )
    if not body.features:
        raise HTTPException(status_code=400, detail="features required for live scoring")
    try:
        w = workspace_client()
        resp = w.serving_endpoints.query(
            name=settings.serving_endpoint,
            dataframe_records=[body.features],
        )
        return {
            "source": "serving_endpoint",
            "endpoint": settings.serving_endpoint,
            "response": str(resp),
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/pipeline/health")
def pipeline_health_route() -> dict[str, Any]:
    try:
        return pipeline_health()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/genie/ask")
def genie_ask_route(body: GenieAskRequest) -> dict[str, Any]:
    try:
        return genie_ask(body.question, body.conversation_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
