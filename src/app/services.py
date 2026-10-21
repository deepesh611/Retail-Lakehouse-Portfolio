"""Shared control-room services used by FastAPI and Streamlit (SDK, no hardcoded tokens)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from config import Settings, get_settings


def workspace_client():
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient()


def mlflow_client():
    import mlflow
    from mlflow.tracking import MlflowClient

    if os.getenv("DATABRICKS_HOST"):
        mlflow.set_tracking_uri("databricks")
        mlflow.set_registry_uri("databricks-uc")
    return MlflowClient()


def default_warehouse_id(w) -> str:
    env = os.getenv("RETAIL_WAREHOUSE_ID")
    if env:
        return env
    warehouses = list(w.warehouses.list())
    if not warehouses:
        raise RuntimeError("No SQL warehouse available in workspace")
    return warehouses[0].id


def statement_rows(result) -> list[dict[str, Any]]:
    manifest = getattr(result, "manifest", None)
    schema = getattr(manifest, "schema", None) if manifest else None
    columns = []
    if schema and getattr(schema, "columns", None):
        columns = [c.name for c in schema.columns]
    chunk = getattr(result, "result", None)
    data_array = getattr(chunk, "data_array", None) or [] if chunk is not None else []
    rows = []
    for arr in data_array:
        if columns:
            rows.append({columns[i]: arr[i] for i in range(min(len(columns), len(arr)))})
        else:
            rows.append({"values": list(arr)})
    return rows


def to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "as_dict"):
        return obj.as_dict()
    if hasattr(obj, "__dict__"):
        return {k: to_dict(v) for k, v in vars(obj).items() if not k.startswith("_")}
    return str(obj)


def get_model_info(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    client = mlflow_client()
    model = client.get_registered_model(settings.model_name)
    aliases = {a.alias: a.version for a in (model.aliases or [])}
    return {
        "name": model.name,
        "description": model.description,
        "aliases": aliases,
        "latest_versions": [
            {"version": v.version, "status": v.status, "run_id": v.run_id}
            for v in (model.latest_versions or [])
        ],
    }


def get_model_versions(name: str) -> dict[str, Any]:
    client = mlflow_client()
    versions = client.search_model_versions(f"name='{name}'")
    return {
        "name": name,
        "versions": [
            {
                "version": v.version,
                "status": v.status,
                "run_id": v.run_id,
                "aliases": list(getattr(v, "aliases", []) or []),
            }
            for v in sorted(versions, key=lambda x: int(x.version), reverse=True)
        ],
    }


def get_experiment_runs(
    settings: Settings | None = None, limit: int = 20
) -> dict[str, Any]:
    settings = settings or get_settings()
    client = mlflow_client()
    exp = client.get_experiment_by_name(settings.experiment_name)
    if exp is None:
        raise LookupError("experiment not found")
    runs = client.search_runs(
        experiment_ids=[exp.experiment_id],
        order_by=["metrics.roc_auc DESC"],
        max_results=min(limit, 100),
    )
    return {
        "experiment_id": exp.experiment_id,
        "experiment_name": settings.experiment_name,
        "runs": [
            {
                "run_id": r.info.run_id,
                "status": r.info.status,
                "start_time": r.info.start_time,
                "metrics": dict(r.data.metrics),
                "params": dict(r.data.params),
            }
            for r in runs
        ],
    }


def get_predictions(settings: Settings | None = None, limit: int = 50) -> dict[str, Any]:
    settings = settings or get_settings()
    w = workspace_client()
    sql = f"""
      SELECT customer_id, region, churn_probability, churn_prediction,
             model_version, model_alias, scored_at
      FROM {settings.predictions_table}
      ORDER BY churn_probability DESC
      LIMIT {int(min(limit, 200))}
    """
    result = w.statement_execution.execute_statement(
        warehouse_id=default_warehouse_id(w),
        statement=sql,
        wait_timeout="50s",
    )
    return {"table": settings.predictions_table, "rows": statement_rows(result)}


def predict_customer(customer_id: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    w = workspace_client()
    safe_id = customer_id.replace("'", "")
    sql = f"""
      SELECT customer_id, region, churn_probability, churn_prediction,
             model_version, model_alias, scored_at
      FROM {settings.predictions_table}
      WHERE customer_id = '{safe_id}'
      LIMIT 1
    """
    result = w.statement_execution.execute_statement(
        warehouse_id=default_warehouse_id(w),
        statement=sql,
        wait_timeout="50s",
    )
    rows = statement_rows(result)
    if not rows:
        raise LookupError("no batch prediction for customer")
    return {"source": "delta_batch", "prediction": rows[0]}


def pipeline_health(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    w = workspace_client()
    pipeline_id = settings.pipeline_id
    pipeline_name = settings.pipeline_name
    if not pipeline_id:
        pipelines = list(w.pipelines.list_pipelines())
        match = [
            p
            for p in pipelines
            if (p.name or "") == settings.pipeline_name
            or settings.pipeline_name in (p.name or "")
        ]
        if not match:
            return {
                "pipeline_name": settings.pipeline_name,
                "status": "not_found",
                "hint": (
                    "Pipeline not visible to this app. Grant the app service "
                    "principal CAN_VIEW, or set RETAIL_PIPELINE_ID."
                ),
            }
        pipeline_id = match[0].pipeline_id
        pipeline_name = match[0].name or pipeline_name
    detail = w.pipelines.get(pipeline_id)
    state = getattr(detail, "state", None)
    pipeline_name = getattr(detail, "name", None) or pipeline_name
    latest = []
    try:
        events = list(w.pipelines.list_pipeline_events(pipeline_id, max_results=5))
        latest = [
            {
                "id": getattr(e, "id", None),
                "timestamp": str(getattr(e, "timestamp", None)),
                "event_type": str(getattr(e, "event_type", None)),
                "level": str(getattr(e, "level", None)),
                "message": str(getattr(e, "message", None))[:300],
            }
            for e in events
        ]
    except Exception:  # noqa: BLE001
        latest = []
    return {
        "pipeline_id": pipeline_id,
        "pipeline_name": pipeline_name,
        "state": str(state),
        "recent_events": latest,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def genie_ask(question: str, conversation_id: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    if not settings.genie_space_id:
        raise RuntimeError(
            "RETAIL_GENIE_SPACE_ID not set. Create a Genie space and configure App env."
        )
    w = workspace_client()
    genie = getattr(w, "genie", None)
    if genie is None:
        raise RuntimeError("Genie SDK surface not available in this workspace/SDK")
    if conversation_id and hasattr(genie, "create_message_and_wait"):
        msg = genie.create_message_and_wait(
            space_id=settings.genie_space_id,
            conversation_id=conversation_id,
            content=question,
        )
        return {"conversation_id": conversation_id, "message": to_dict(msg)}
    if hasattr(genie, "start_conversation_and_wait"):
        conv = genie.start_conversation_and_wait(
            space_id=settings.genie_space_id,
            content=question,
        )
        return {"result": to_dict(conv)}
    raise RuntimeError("Genie conversation methods missing")
