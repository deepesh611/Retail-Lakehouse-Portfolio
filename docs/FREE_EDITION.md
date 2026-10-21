# Free Edition constraints and workarounds

Source: [Databricks Free Edition limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)

| Constraint | How this project works around it |
|---|---|
| Serverless only | All Jobs use `environment_key` serverless envs; pipeline `serverless: true` |
| 1× SQL warehouse `2X-Small` | Dashboards/Genie/App SQL share one warehouse; keep queries on gold |
| ≤5 concurrent job tasks | Jobs are single-task or a 3-task sequential ML DAG |
| 1 active Lakeflow pipeline per type | One bronze→silver→gold pipeline |
| Apps stop after ~24h (max 3) | Document restart-before-demo; one control-room App |
| No GPU serving; limited custom serving | Batch scoring Job is primary; serving opt-in via `.yml.example` |
| Restricted outbound internet | Synthetic data generated in-workspace (Faker), no web scrape |
| Non-commercial + inactivity risk | **GitHub repo + README + diagram + demo video** are the durable portfolio |
| No SSO/SCIM | Governance shown via masked/region views + documented grant model |

## LinkedIn verification

If the workspace shows **Verify identity**, complete it for higher limits (including limited serverless GPU). It does not remove all Free Edition restrictions.

## Serving fallback

`var.enable_serving` defaults to `false`. The App `/predict` looks up `churn_predictions` by `customer_id`. To enable live CPU serving when available:

1. Copy `resources/serving/churn_endpoint.yml.example` into a live resource file
2. Deploy a trained model version
3. Set App env `RETAIL_ENABLE_SERVING=true`
