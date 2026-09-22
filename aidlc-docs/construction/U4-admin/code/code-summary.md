# U4 Admin & Configuration — Code Summary

## Generated Files (`src/modules/admin/`)
- `schemas.py` — admin DTOs (instance/routing/mapping requests + views, ConfigView, MappingReport, ConnectivityResult)
- `repositories.py` — InstanceRepository, RoutingRuleRepository, MappingRepository (config CRUD)
- `service.py` — AdminService: register_instance, check_connectivity (via U3 adapters), define_routing_rule (active-target validation), reorder_rules, save_mapping (+ completeness report), get_config
- `router.py` — /admin/instances, /admin/instances/{id}/connectivity, /admin/routing-rules, /admin/routing-rules/order, /admin/mappings, /admin/config; all require_role("ADMIN")

## Other changes
- `src/app/main.py` — includes admin router

## Story Traceability
- US-6.1 register instance ✅
- US-6.2 routing rules authoring + reorder ✅
- US-6.3 mapping authoring + completeness report ✅
- US-6.4 view config ✅

## Verification Status (honest)
- Authored against U4 design. **Tests NOT executed here** (no Python/Docker). DB-free test (mapping completeness) ready under pytest; full CRUD/DB + connectivity paths in Build & Test.

## Notes / Accepted Risks
- Minimal admin = JSON API (no served HTML for MVP).
- ERP connection_ref stored inline (Q7=A) — flagged for hardening.
