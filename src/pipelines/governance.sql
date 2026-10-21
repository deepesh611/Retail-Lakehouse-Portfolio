-- Governance demos for Free Edition (single-user workspace).
-- Column mask via UDF + secured views; region filter via demo views.
-- SSO/SCIM multi-role grants are unsupported on Free Edition — documented only.

-- Table-level tags
ALTER TABLE ${catalog}.${schema}.gold_customer_360
SET TAGS ('domain' = 'retail', 'layer' = 'gold', 'certified' = 'true');

-- Column-level PII tags
ALTER TABLE ${catalog}.${schema}.gold_customer_360
ALTER COLUMN email SET TAGS ('pii' = 'email', 'sensitivity' = 'high');

ALTER TABLE ${catalog}.${schema}.gold_customer_360
ALTER COLUMN full_name SET TAGS ('pii' = 'name', 'sensitivity' = 'medium');

-- Masking UDF
CREATE OR REPLACE FUNCTION ${catalog}.${schema}.mask_email(email STRING)
RETURNS STRING
RETURN CASE
  WHEN email IS NULL THEN NULL
  WHEN locate('@', email) = 0 THEN '***'
  ELSE concat(left(email, 2), '***@', element_at(split(email, '@'), 2))
END;

-- Secured view: masked email
CREATE OR REPLACE VIEW ${catalog}.${schema}.gold_customer_360_masked AS
SELECT
  customer_id,
  ${catalog}.${schema}.mask_email(email) AS email,
  full_name,
  region,
  signup_date,
  loyalty_tier,
  is_active,
  order_count,
  lifetime_revenue,
  avg_order_value,
  last_order_ts,
  first_order_ts,
  event_count,
  purchase_events,
  days_since_last_order,
  churn_label
FROM ${catalog}.${schema}.gold_customer_360;

-- Demo region-scoped view (simulates regional manager row filter for 'north')
CREATE OR REPLACE VIEW ${catalog}.${schema}.gold_customer_360_region_north AS
SELECT *
FROM ${catalog}.${schema}.gold_customer_360_masked
WHERE region = 'north';

-- Intended grant model when multi-user IAM is available:
-- GRANT SELECT ON VIEW ${catalog}.${schema}.gold_customer_360_masked TO `analysts`;
-- GRANT SELECT ON VIEW ${catalog}.${schema}.gold_customer_360_region_north TO `regional_managers_north`;
-- REVOKE SELECT ON TABLE ${catalog}.${schema}.gold_customer_360 FROM `analysts`;
