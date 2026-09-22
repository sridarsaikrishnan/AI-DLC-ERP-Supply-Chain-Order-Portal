# Business Logic Model — U2 Ordering & Lifecycle

## Process 1: Place Order (US-2.1/2.2)
- Input: SecurityContext (U1), canonical order body
- Logic: stamp tenantId from context; validate canonical (U0 BR-1); if invalid -> 400 with field errors; persist order (state=Submitted) via U0 tenant-scoped repo; enqueue SUBMISSION job (U0 queue, dedupe_key=order_id); return ack {orderId, Submitted}.
- Output: order ack or validation errors.

## Process 2: Browse Catalog / Check Inventory (US-3.1/3.2, Q1=B/Q2=B)
- Logic: serve from a portal-side seed/cache for MVP; scoped to a default/primary instance. Live ERP fetch via U3 is the documented target.
- Output: canonical products / availability, or empty-state.

## Process 3: List / Get Order + History (US-4.1/4.2/4.3)
- Logic: tenant-scoped reads (U0 fail-closed). Detail includes current lifecycle state + erp_reference; history returns transitions chronologically. Status reflects U3-applied updates.

## Process 4: Corrective Action (US-5.1/5.2/5.3, Q3=A async, Q4=A)
- Logic: authorize (U1, >= CLIENT_USER); check current state permits the action; for AMEND, re-validate the full amended canonical order (BR-1); enqueue CORRECTIVE_ACTION job (dedupe_key=order_id+action+version); return "accepted". Execution + result handled by U3, reflected in lifecycle.

## Data Flow (text)
```
POST /orders -> Process 1 -> persist + enqueue SUBMISSION -> ack
GET /orders, /orders/{id}, /orders/{id}/history -> Process 3 (tenant-scoped)
GET /catalog, /inventory -> Process 2 (seed/default instance)
POST /orders/{id}/{cancel|amend|resubmit} -> Process 4 -> enqueue CORRECTIVE_ACTION -> ack
```
