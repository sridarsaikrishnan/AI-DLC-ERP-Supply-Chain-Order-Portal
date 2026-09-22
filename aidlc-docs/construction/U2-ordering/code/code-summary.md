# U2 Ordering & Lifecycle — Code Summary

## Generated Files (`src/modules/ordering/`)
- `schemas.py` — request/response DTOs (PlaceOrderRequest, AmendRequest, OrderAck, OrderView, StatusHistoryView, ProductView, InventoryView, ActionAck)
- `catalog_service.py` — seed catalog + inventory (Q1=B/Q2=B)
- `repositories.py` — OrderRepository (U0 TenantScopedRepository subclass), StatusHistoryRepository
- `service.py` — OrderService: place_order (validate->persist->enqueue SUBMISSION), list/get/history, initiate_corrective (state+role gating, amend re-validate, enqueue CORRECTIVE_ACTION)
- `router.py` — /orders (POST, GET, GET/{id}, GET/{id}/history), /orders/{id}/cancel|resubmit|amend, /catalog, /inventory/{product_key}; guarded by U1 deps

## Other changes
- `src/app/main.py` — includes ordering router

## Story Traceability
- US-2.1/2.2 place + ack ✅
- US-3.1/3.2 catalog/inventory ✅ (seed)
- US-4.1/4.2/4.3 list/detail/history/status ✅
- US-5.1/5.2/5.3 resubmit/cancel/amend ✅ (async -> U3)

## Verification Status (honest)
- Authored against U2 design. **Tests NOT executed here** (no Python/Docker). DB-free tests (catalog, validation gate) ready under pytest; full API/DB flows (place->enqueue->U3->status) run in Build & Test.

## Notes
- Tenant id always taken from the U1 token context, never the request body (BR-U2-1.1).
- Corrective actions async (ack then U3 executes); amend fully re-validates (Q3/Q4).
