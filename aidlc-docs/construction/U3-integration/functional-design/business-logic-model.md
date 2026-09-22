# Business Logic Model — U3 Integration

## Process 1: Process Submission (SUBMISSION job handler)
- Input: job payload { order_id, tenant_id }
- Logic:
  1. Load order + canonical payload (U0 repo).
  2. Route via U0 `evaluate_routing(rules, order_dict)`.
  3. If NoMatch -> mark order Failed, reason "no route matched" (BR-U3-2, Q4=A). Stop.
  4. Load TO_ERP mapping for (instance, SALES_ORDER); apply mapping -> ErpPayload.
  5. Call adapter.submit(payload, connection).
  6. On success -> record Accepted + erp_reference. On terminal failure -> Failed. On transient -> raise (U0 retry).

## Process 2: Process Status Sync (STATUS_SYNC job handler, Q3=A polling)
- Input: job payload { order_id } (or a sweep over open orders)
- Logic: adapter.fetch_status -> map FROM_ERP native->canonical LifecycleState -> apply status update (latest-wins) + history.

## Process 3: Process Corrective Action (CORRECTIVE_ACTION job handler)
- Input: { order_id, action: CANCEL|AMEND|RESUBMIT, amended_payload? }
- Logic:
  - RESUBMIT: re-run Process 1 pipeline for the order.
  - CANCEL/AMEND: map as needed, call adapter.send_corrective_action; on success record new state (Cancelled/Amended); on rejection surface reason and keep prior state (BR-U3-3).

## Process 4: Mapping Application (Q1=A)
- toErp(canonical, mapping): apply field_entries (+ value_map), expressions as direct copies.
- fromErp(native, mapping): reverse for status/inventory/product reads.

## Adapter Contract & Stubs (Q2=B)
- ErpNextStubAdapter / OdooStubAdapter simulate: accept submit -> return generated erp_reference; fetch_status -> progress through states deterministically; corrective actions -> accept unless simulated "already shipped".

## Data Flow (text)
```
U0 worker -> SUBMISSION handler (Process 1): route -> map -> adapter.submit -> lifecycle update
scheduler -> STATUS_SYNC handler (Process 2): fetch -> map -> lifecycle update
U2 enqueues CORRECTIVE_ACTION -> handler (Process 3): map -> adapter action -> lifecycle update
```

## Notes
- Mapping application (Process 4) is deterministic — a candidate for partial PBT round-trip tests (canonical->erp->canonical for field-entry maps).
- No auto-failover (Q4=A); transient errors rely on U0 bounded retry.
