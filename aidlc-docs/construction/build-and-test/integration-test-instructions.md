# Integration Test Instructions

Integration tests exercise interactions across units against a real PostgreSQL (via docker compose).

## Setup
```bash
docker compose up --build   # postgres + 2 app replicas + nginx
```
Seed users (from migration 002): `admin/admin123` (ADMIN), `client/client123` (CLIENT_USER).

## Scenario 1: Auth -> tenant-scoped access (U1 + U0)
1. `POST /auth/login` {username: client, password: client123} -> token.
2. `GET /orders` with `Authorization: Bearer <token>` -> only the caller's tenant orders (empty initially).
3. Call `GET /orders` with no token -> 401.

## Scenario 2: Admin config -> routing/mapping (U4 + U0)
1. Login as admin -> token.
2. `POST /admin/instances` {erp_type: ERP_NEXT, display_name: "ERPNext EU", connection_ref: "stub"} -> instance id.
3. `POST /admin/routing-rules` {order_index:1, conditions:[{field:"currency",operator:"EQUALS",value:"USD"}], target_instance_id:<id>, enabled:true}.
4. `POST /admin/mappings` {instance_id:<id>, data_type:SALES_ORDER, direction:TO_ERP, field_entries:[...]} -> MappingReport (note unmapped required warnings).
5. `GET /admin/config` -> reflects the above.

## Scenario 3: Place order -> async fulfillment -> status (U2 + U0 queue + U3)
1. Login as client -> token.
2. `POST /orders` with a valid canonical order whose content matches a routing rule -> `{order_id, Submitted}`.
3. Wait for the poller (1-2s) to process the SUBMISSION job -> `GET /orders/{id}` shows `Accepted` with an `erp_reference` (stub).
4. Trigger `STATUS_SYNC` (scheduled or manual enqueue) -> status advances (Processing/Shipped/Invoiced) on subsequent polls.
5. `GET /orders/{id}/history` -> chronological transitions.

## Scenario 4: Corrective actions (U2 + U3)
1. `POST /orders/{id}/cancel` before shipped -> accepted -> status Cancelled.
2. `POST /orders/{id}/cancel` after shipped -> stub rejects; order keeps prior state, reason surfaced in history.

## Cleanup
```bash
docker compose down -v
```

## Notes
- MVP uses stub ERP adapters, so no live ERP is needed.
- No-match routing -> order marked Failed with "no route matched".
