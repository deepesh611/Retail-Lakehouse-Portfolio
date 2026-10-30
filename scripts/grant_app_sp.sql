-- Grant the Control Room App service principal the UC privileges it needs.
-- Use the SP applicationId (display names with spaces are not resolved by UC).
-- App SP: app-2snpls retail-churn-control-room-dev
-- applicationId: fc782214-3e40-4e4d-b6b2-e409adba8b69

GRANT USE CATALOG ON CATALOG workspace
  TO `fc782214-3e40-4e4d-b6b2-e409adba8b69`;

GRANT USE SCHEMA ON SCHEMA workspace.dev_deepeshvcd6273_retail_dev
  TO `fc782214-3e40-4e4d-b6b2-e409adba8b69`;

GRANT SELECT ON SCHEMA workspace.dev_deepeshvcd6273_retail_dev
  TO `fc782214-3e40-4e4d-b6b2-e409adba8b69`;

-- Registered UC models are function securables; use the grants API if SQL MODEL syntax fails:
--   databricks grants update function workspace.<schema>.churn_model --json ...
