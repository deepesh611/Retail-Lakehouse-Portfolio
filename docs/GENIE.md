# Genie space setup (Phase 1D / 3A)

## Create the space

1. In the workspace, open **Genie**.
2. Create a space over certified gold objects only:
   - `{catalog}.{schema}.gold_customer_360`
   - `{catalog}.{schema}.gold_order_facts`
   - `{catalog}.{schema}.gold_region_kpis`
   - `{catalog}.{schema}.gold_customer_360_masked` (optional)
3. Add instructions (paste below).
4. Add sample questions.
5. Copy the **space id** into App env `RETAIL_GENIE_SPACE_ID` for Phase 3.

## Instructions (curated)

```
You are a retail analytics assistant for an e-commerce lakehouse.
Only answer from the certified gold tables provided.
Regions are: north, south, east, west, central.
churn_label = 1 means the customer looks churned (inactive or >90 days since last order).
Prefer aggregations; do not invent columns.
Currency amounts are in USD.
```

## Sample questions

1. Which region has the highest lifetime revenue?
2. How many customers have churn_label = 1?
3. What is the average order value by loyalty_tier?
4. Top 10 customers by lifetime_revenue in the north region?
5. How many completed orders per channel?
6. What share of customers have no orders in the last 90 days?
7. Compare event_count between churned and active customers.
8. Daily order counts for the last 30 days of data.

## Gate

Genie must answer questions 1–3 correctly before Phase 1E exit / Phase 3 App wiring.
