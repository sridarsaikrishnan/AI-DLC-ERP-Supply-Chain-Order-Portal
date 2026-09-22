# U3 Integration — Code Summary

## Generated Files (`src/modules/integration/`)
- `adapter.py` — ErpAdapter protocol, AdapterResult (terminal flag), AdapterRegistry, AdapterAction
- `adapters/erpnext_stub.py`, `adapters/odoo_stub.py` — simulators (submit, status progression, corrective w/ already-shipped reject)
- `mapping_engine.py` — apply_mapping / to_erp / from_erp (field entries + value maps; nested paths); pure (PBT candidate)
- `routing_service.py` — loads RoutingRuleRow -> U0 evaluate_routing
- `handlers.py` — process_submission / process_status_sync / process_corrective_action; transient (raise) vs terminal (Failed); lifecycle + history writes
- `bootstrap.py` — registers stub adapters + handlers into U0 HandlerRegistry

## Other changes
- `src/app/main.py` — calls `register_integration(handler_registry)` at import/startup
- `tests/integration/test_mapping_and_routing.py` — mapping (value map + nested), adapter registry/submit, cancel-after-shipped reject

## Story Traceability
- E2–E5 async fulfillment -> handlers ✅
- US-6.2 runtime routing -> RoutingService ✅
- US-6.3 runtime mapping -> MappingEngine ✅

## Verification Status (honest)
- Authored against U3 design. **Tests NOT executed here** (no Python/Docker in env). DB-free tests (mapping, routing pure eval, stub adapters) ready under pytest. Full handler DB paths (submission->lifecycle) run in Build & Test.

## Notes / Accepted Risks
- Stub adapters only (Q2=B); real ERP HTTP adapters are a later drop-in behind ErpAdapter.
- ERP connection_ref used as-is (Q7=A) — flagged for hardening.
- No auto-failover (Q4=A); transient failures rely on U0 retry.
