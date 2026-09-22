# Logical Components — U3 Integration

Placed in `src/modules/integration/`.

## LC-U3-1: AdapterRegistry + ErpAdapter interface
- `adapter.py` — ErpAdapter protocol, AdapterResult, AdapterRegistry (ErpType -> adapter).

## LC-U3-2: Stub Adapters
- `adapters/erpnext_stub.py`, `adapters/odoo_stub.py` — simulate submit/status/corrective.

## LC-U3-3: MappingEngine
- `mapping_engine.py` — to_erp / from_erp using U0 MappingDefinition (field entries + value maps; expressions as copies).

## LC-U3-4: RoutingService
- `routing_service.py` — loads rules via U0 config resolver, calls U0 evaluate_routing.

## LC-U3-5: Handlers
- `handlers.py` — process_submission, process_status_sync, process_corrective_action; registered into U0 HandlerRegistry at startup.

## LC-U3-6: Registration hook
- `bootstrap.py` — wires adapters + handlers into U0 HandlerRegistry (called from app startup).

## Module Placement
```
src/modules/integration/
├── adapter.py
├── adapters/
│   ├── erpnext_stub.py
│   └── odoo_stub.py
├── mapping_engine.py
├── routing_service.py
├── handlers.py
└── bootstrap.py
```
