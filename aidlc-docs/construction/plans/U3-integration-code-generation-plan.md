# Code Generation Plan — U3 Integration

## Unit Context
- **Unit**: U3 Integration (async engine: routing, mapping execution, ERP adapters, worker handlers, status sync).
- **Depends on**: U0 (queue/HandlerRegistry, config resolver, canonical models, persistence, routing evaluation).
- **MVP**: stub adapters (Q2=B); polling status sync (Q3=A); mark-Failed no failover (Q4=A); field-entry+value-map mapping (Q1=A).
- **Accepted risk (Q7=A)**: inline ERP credentials in config.

## Target Structure
```
src/modules/integration/
├── adapter.py            # ErpAdapter protocol, AdapterResult, AdapterRegistry
├── adapters/
│   ├── erpnext_stub.py
│   └── odoo_stub.py
├── mapping_engine.py     # to_erp / from_erp (field entries + value maps)
├── routing_service.py    # load rules -> U0 evaluate_routing
├── handlers.py           # process_submission / process_status_sync / process_corrective_action
└── bootstrap.py          # register adapters + handlers into U0 HandlerRegistry
tests/integration/        # mapping round-trip, routing, adapter/handler behavior
```

## Generation Steps
- [x] **Step 1 — Adapter interface & registry** (`adapter.py`).
- [x] **Step 2 — Stub adapters** (`adapters/erpnext_stub.py`, `adapters/odoo_stub.py`).
- [x] **Step 3 — MappingEngine** (`mapping_engine.py`).
- [x] **Step 4 — RoutingService** (`routing_service.py`).
- [x] **Step 5 — Handlers** (`handlers.py`): submission/status-sync/corrective; transient vs terminal + lifecycle writes.
- [x] **Step 6 — Bootstrap** (`bootstrap.py`): registers adapters + handlers into U0; wired into `main.py`.
- [x] **Step 7 — Lifecycle helper**: implemented inline in handlers (`_record_status`) writing to U0 order/status tables.
- [x] **Step 8 — Unit tests** (`tests/integration/test_mapping_and_routing.py`).
- [x] **Step 9 — Documentation** (`code-summary.md`).

## Story Traceability
- E2–E5 fulfillment (async) -> handlers (Step 5)
- US-6.2 runtime routing -> RoutingService (Step 4)
- US-6.3 runtime mapping -> MappingEngine (Step 3)

## Verification Note
Same environment limitation (no runnable Python/Docker). DB-free tests (mapping round-trip, routing, stub adapters, pure handler logic with fakes) authored to run under pytest; full DB-backed handler paths in Build & Test.
