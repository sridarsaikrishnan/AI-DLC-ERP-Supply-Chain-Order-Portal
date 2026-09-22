# Code Generation Plan — U2 Ordering & Lifecycle

## Unit Context
- **Unit**: U2 client-facing ordering + lifecycle + catalog/inventory lookups.
- **Depends on**: U0 (canonical validate, order/status tables, tenant repos, queue), U1 (auth deps), U3 (async fulfillment via enqueued jobs).
- **Decisions**: catalog/inventory from seed against default instance (Q1=B/Q2=B); corrective actions async (Q3=A); amend full re-validate (Q4=A).

## Target Structure
```
src/modules/ordering/
├── schemas.py           # request/response DTOs
├── catalog_service.py   # seed catalog + inventory
├── service.py           # OrderService: place, list/get, history, corrective
└── router.py            # endpoints, guarded by U1 deps
tests/ordering/          # order service + validation + corrective-state tests
```

## Generation Steps
- [x] **Step 1 — DTOs** (`schemas.py`).
- [x] **Step 2 — Repositories** (`repositories.py`): OrderRepository (U0 TenantScopedRepository subclass) + StatusHistoryRepository.
- [x] **Step 3 — CatalogService** (`catalog_service.py`): seed catalog + inventory.
- [x] **Step 4 — OrderService** (`service.py`): place_order, list/get/history, initiate_corrective (state+role gating, amend re-validate).
- [x] **Step 5 — Router** (`router.py`): order/catalog/inventory/corrective endpoints via U1 deps; wired into main.py.
- [x] **Step 6 — Unit tests** (`tests/ordering/test_ordering.py`).
- [x] **Step 7 — Documentation** (`code-summary.md`).

## Story Traceability
- US-2.1/2.2 place + ack -> Steps 1,2,4,5
- US-3.1/3.2 catalog/inventory -> Steps 3,5
- US-4.1/4.2/4.3 list/detail/history/status -> Steps 2,4,5
- US-5.1/5.2/5.3 resubmit/cancel/amend -> Step 4,5 (enqueue -> U3)

## Verification Note
Same environment limitation. DB-free tests via fakes; full API/DB paths in Build & Test.
