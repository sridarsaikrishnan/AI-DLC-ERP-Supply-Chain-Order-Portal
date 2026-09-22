# Business Rules — U4 Admin & Configuration

## BR-U4-1: Authorization
- All admin operations require ADMIN role (U1). Non-admins get 403.

## BR-U4-2: Instance Registration (US-6.1)
- erp_type must be a supported type (ERP_NEXT, ODOO for MVP); connection_ref required.
- Invalid/incomplete details -> validation error, nothing persisted.
- Connectivity check reports reachable/unreachable via the adapter (stub returns reachable).

## BR-U4-3: Routing Rules (US-6.2)
- target_instance_id must reference an existing active instance (BR-4.3).
- order_index defines precedence; reorder sets it explicitly.
- Overlapping rules are allowed; first-match-wins by order_index at runtime (U0/U3).

## BR-U4-4: Mappings (US-6.3)
- MappingDefinition must reference an existing instance.
- Required canonical fields without a mapping entry are reported as warnings (mapping completeness, BR-4.4).

## BR-U4-5: Config View (US-6.4)
- Returns the latest saved instances, rules (ordered), and mappings; reflects most recent changes.

## BR-U4-6: Config is platform-scoped
- Config is not tenant-owned; governed by admin authorization, not tenant filtering (consistent with U0 BR-2.4).
