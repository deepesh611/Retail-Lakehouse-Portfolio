# AI/BI dashboard (Phase 1D)

Build a curated dashboard on the SQL warehouse (`2X-Small`) using gold tables only.

## Datasets

- `{catalog}.{schema}.gold_region_kpis`
- `{catalog}.{schema}.gold_customer_360`
- `{catalog}.{schema}.gold_order_facts`

## Suggested tiles

1. **Revenue by region** — bar on `gold_region_kpis.revenue`
2. **Orders by region** — bar on `orders`
3. **Churn rate** — `avg(churn_label)` on `gold_customer_360`
4. **Repeat customers** — count where `order_count >= 2`
5. **AOV by loyalty tier** — `avg(avg_order_value)` grouped by `loyalty_tier`

## Example SQL

```sql
SELECT region, revenue, orders, active_customers, avg_order_value
FROM workspace.retail_dev.gold_region_kpis
ORDER BY revenue DESC;

SELECT
  ROUND(AVG(churn_label), 3) AS churn_rate,
  COUNT(*) AS customers
FROM workspace.retail_dev.gold_customer_360;

SELECT loyalty_tier,
       ROUND(AVG(avg_order_value), 2) AS aov,
       COUNT(*) AS customers
FROM workspace.retail_dev.gold_customer_360
GROUP BY loyalty_tier
ORDER BY aov DESC;
```

## Gate

Dashboard loads without warehouse timeout on Free Edition. Keep extracts small — no bronze scans.
