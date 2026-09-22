# Logical Components — U2 Ordering & Lifecycle

Placed in `src/modules/ordering/`.

- **LC-U2-1 OrderService** (`service.py`): place_order, list/get, history, initiate corrective; uses U0 repos + queue enqueue.
- **LC-U2-2 CatalogService** (`catalog_service.py`): seed/cache catalog + inventory (Q1=B/Q2=B).
- **LC-U2-3 DTOs** (`schemas.py`): request/response models.
- **LC-U2-4 Router** (`router.py`): `/orders`, `/orders/{id}`, `/orders/{id}/history`, `/orders/{id}/cancel|amend|resubmit`, `/catalog`, `/inventory`; guarded by U1 deps.

```
src/modules/ordering/
├── schemas.py
├── catalog_service.py
├── service.py
└── router.py
```
