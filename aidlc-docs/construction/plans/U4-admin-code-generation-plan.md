# Code Generation Plan — U4 Admin & Configuration (final unit)

## Unit Context
- **Unit**: U4 minimal admin API — register ERP instances, manage routing rules + mappings, view config.
- **Depends on**: U0 (config tables/models), U1 (ADMIN guard), U3 (adapter connectivity check).
- **Surface**: JSON API (no served HTML for MVP). ADMIN role required on all routes.

## Target Structure
```
src/modules/admin/
├── schemas.py        # admin DTOs
├── repositories.py   # config CRUD (instances, routing rules, mappings)
├── service.py        # AdminService
└── router.py         # /admin/* endpoints, require_role("ADMIN")
tests/admin/          # config CRUD + authorization + mapping completeness
```

## Generation Steps
- [x] **Step 1 — DTOs** (`schemas.py`).
- [x] **Step 2 — Config repositories** (`repositories.py`).
- [x] **Step 3 — AdminService** (`service.py`): register instance, define/reorder rules (active-target validation), save mapping (+ completeness), get config, connectivity.
- [x] **Step 4 — Router** (`router.py`): all /admin/* endpoints require_role("ADMIN"); wired into main.py.
- [x] **Step 5 — Unit tests** (`tests/admin/test_admin_service.py`).
- [x] **Step 6 — Documentation** (`code-summary.md`).

## Story Traceability
- US-6.1 register instance -> Steps 2,3,4
- US-6.2 routing rules authoring -> Steps 2,3,4
- US-6.3 mapping authoring -> Steps 2,3,4
- US-6.4 view config -> Steps 3,4

## Verification Note
Same environment limitation. DB-free tests via fakes; full CRUD/DB paths in Build & Test.
