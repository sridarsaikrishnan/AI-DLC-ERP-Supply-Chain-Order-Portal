# Domain Entities — U4 Admin & Configuration

U4 reuses the U0 config domain (ErpInstance, RoutingRule/RoutingCondition, MappingDefinition/MappingEntry) and their tables. It defines admin API DTOs.

## Request DTOs
- `RegisterInstanceRequest` — { erp_type, display_name, connection_ref }
- `RoutingRuleRequest` — { order_index, conditions[], target_instance_id, enabled }
- `ReorderRequest` — { ordered_rule_ids[] }
- `MappingRequest` — { instance_id, data_type, direction, field_entries[] }

## Response DTOs
- `InstanceView`, `RoutingRuleView`, `MappingView`
- `ConfigView` — { instances[], routing_rules[], mappings[] }
- `MappingReport` — { unmapped_required[], warnings[] }
- `ConnectivityResult` — { instance_id, reachable }

## Reused (U0)
- ErpInstanceRow, RoutingRuleRow, MappingDefinitionRow and the config Pydantic models.
