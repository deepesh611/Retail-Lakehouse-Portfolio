# Landing file schemas

## customers (`customers/ingest_date=YYYY-MM-DD/*.json`)

| Field | Type | Notes |
|---|---|---|
| customer_id | string | `C######` |
| email | string | PII |
| full_name | string | PII |
| region | string | north/south/east/west/central |
| signup_date | string ISO date | |
| loyalty_tier | string | bronze/silver/gold/platinum |
| is_active | bool | |

## orders

| Field | Type | Notes |
|---|---|---|
| order_id | string\|null | null rows injected for quarantine demo |
| customer_id | string | |
| order_ts | string | |
| amount | double | negatives injected for quarantine |
| channel | string | |
| region | string | `INVALID` injected for quarantine |
| status | string | completed/cancelled/returned |

## clickstream

| Field | Type |
|---|---|
| event_id | string |
| customer_id | string |
| event_ts | string |
| event_type | string |
| session_id | string |
| page | string |
