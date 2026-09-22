# Logical Components — U4 Admin & Configuration

Placed in `src/modules/admin/`.

- **LC-U4-1 AdminService** (`service.py`): register/update instance, define/reorder routing rules, save mapping (+ completeness report), get config, connectivity check.
- **LC-U4-2 Config repositories** (`repositories.py`): CRUD over ErpInstanceRow, RoutingRuleRow, MappingDefinitionRow.
- **LC-U4-3 DTOs** (`schemas.py`).
- **LC-U4-4 Router** (`router.py`): /admin/instances, /admin/routing-rules, /admin/routing-rules/order, /admin/mappings, /admin/config; guarded by require_role("ADMIN").

```
src/modules/admin/
├── schemas.py
├── repositories.py
├── service.py
└── router.py
```
