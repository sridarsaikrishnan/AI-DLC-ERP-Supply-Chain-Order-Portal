"""AdminService (LC-U4-1). Manages ERP instances, routing rules, mappings, config view.

Required canonical fields per data type used for the mapping completeness check (BR-4.4).
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from ..foundation.config.models import DataType, ErpType
from ..foundation.persistence.tables import (
    ErpInstanceRow,
    MappingDefinitionRow,
    RoutingRuleRow,
)
from ..integration.adapter import AdapterRegistry
from ...shared.errors import ConfigurationError, NotFoundError
from .repositories import InstanceRepository, MappingRepository, RoutingRuleRepository

# Minimal required canonical fields for completeness reporting.
_REQUIRED_FIELDS = {
    DataType.SALES_ORDER: ["client_reference", "currency", "line_items"],
}


class AdminService:
    def __init__(self, session: Session, adapters: AdapterRegistry | None = None):
        self.session = session
        self.instances = InstanceRepository(session)
        self.rules = RoutingRuleRepository(session)
        self.mappings = MappingRepository(session)
        self.adapters = adapters

    # --- Instances (US-6.1) ---
    def register_instance(self, erp_type: ErpType, display_name: str, connection_ref: str) -> ErpInstanceRow:
        if not connection_ref:
            raise ConfigurationError("connection_ref is required")
        row = ErpInstanceRow(
            id=f"inst-{uuid.uuid4().hex[:8]}",
            erp_type=erp_type.value if hasattr(erp_type, "value") else erp_type,
            display_name=display_name,
            connection_ref=connection_ref,
            status="active",
        )
        self.instances.save(row)
        return row

    def check_connectivity(self, instance_id: str) -> bool:
        instance = self.instances.get(instance_id)
        if instance is None:
            raise NotFoundError("instance not found")
        if self.adapters is None:
            return False
        adapter = self.adapters.get(ErpType(instance.erp_type))
        return bool(adapter and adapter.check_connectivity(instance.connection_ref))

    # --- Routing rules (US-6.2) ---
    def define_routing_rule(self, order_index: int, conditions: list[dict], target_instance_id: str, enabled: bool) -> RoutingRuleRow:
        target = self.instances.get(target_instance_id)
        if target is None or target.status != "active":
            raise ConfigurationError("target_instance_id must reference an active instance")
        row = RoutingRuleRow(
            id=f"rule-{uuid.uuid4().hex[:8]}",
            order_index=order_index,
            conditions=conditions,
            target_instance_id=target_instance_id,
            enabled=enabled,
        )
        self.rules.save(row)
        return row

    def reorder_rules(self, ordered_rule_ids: list[str]) -> None:
        for idx, rule_id in enumerate(ordered_rule_ids):
            row = self.rules.get(rule_id)
            if row is None:
                raise NotFoundError(f"rule {rule_id} not found")
            row.order_index = idx
        self.session.flush()

    # --- Mappings (US-6.3) ---
    def save_mapping(self, instance_id: str, data_type, direction, field_entries: list[dict]):
        if self.instances.get(instance_id) is None:
            raise NotFoundError("instance not found")
        row = MappingDefinitionRow(
            id=f"map-{uuid.uuid4().hex[:8]}",
            instance_id=instance_id,
            data_type=data_type.value if hasattr(data_type, "value") else data_type,
            direction=direction.value if hasattr(direction, "value") else direction,
            field_entries=field_entries,
            expressions=[],
        )
        self.mappings.save(row)
        unmapped = self._unmapped_required(data_type, field_entries)
        return row, unmapped

    @staticmethod
    def _unmapped_required(data_type, field_entries: list[dict]) -> list[str]:
        dt = data_type if isinstance(data_type, DataType) else DataType(data_type)
        required = _REQUIRED_FIELDS.get(dt, [])
        mapped_sources = {e.get("source_path") for e in field_entries}
        return [f for f in required if f not in mapped_sources]

    # --- Config view (US-6.4) ---
    def get_config(self) -> dict:
        return {
            "instances": self.instances.all(),
            "routing_rules": self.rules.ordered(),
            "mappings": self.mappings.all(),
        }
