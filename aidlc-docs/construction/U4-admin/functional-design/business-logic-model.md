# Business Logic Model — U4 Admin & Configuration

Minimal internal admin surface (JSON API for MVP). All operations require ADMIN role (U1). Manages the U0 config domain (ErpInstance, RoutingRule, MappingDefinition).

## Process 1: Register / Update ERP Instance (US-6.1)
- Validate details (erp_type in {ERP_NEXT, ODOO}, connection_ref present); persist instance; optional connectivity check via U3 adapter registry.

## Process 2: Define / Order Routing Rules (US-6.2 authoring)
- Create/update rule (order_index, conditions, target_instance_id, enabled); validate target references an active instance; reorder by supplying ordered ids.

## Process 3: Manage Mapping Definitions (US-6.3 authoring)
- Create/update MappingDefinition (instance, data_type, direction, field_entries); report unmapped required fields (mapping completeness, BR-4.4).

## Process 4: View Configuration (US-6.4)
- Return current instances, routing rules (ordered), and mappings.

## Data Flow (text)
```
POST /admin/instances            -> Process 1 (+ optional connectivity)
POST /admin/routing-rules        -> Process 2
PUT  /admin/routing-rules/order  -> Process 2 (reorder)
POST /admin/mappings             -> Process 3
GET  /admin/config               -> Process 4
```
All guarded by require_role("ADMIN").
