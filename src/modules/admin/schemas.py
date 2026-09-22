"""U4 admin API DTOs (LC-U4-3)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..foundation.config.models import (
    ConditionOperator,
    DataType,
    Direction,
    ErpType,
)


class RegisterInstanceRequest(BaseModel):
    erp_type: ErpType
    display_name: str
    connection_ref: str


class ConditionDTO(BaseModel):
    field: str
    operator: ConditionOperator
    value: object


class RoutingRuleRequest(BaseModel):
    order_index: int
    conditions: list[ConditionDTO] = Field(default_factory=list)
    target_instance_id: str
    enabled: bool = True


class ReorderRequest(BaseModel):
    ordered_rule_ids: list[str]


class MappingEntryDTO(BaseModel):
    source_path: str
    target_path: str
    value_map: dict[str, str] | None = None


class MappingRequest(BaseModel):
    instance_id: str
    data_type: DataType
    direction: Direction
    field_entries: list[MappingEntryDTO] = Field(default_factory=list)


class InstanceView(BaseModel):
    instance_id: str
    erp_type: str
    display_name: str
    status: str


class RoutingRuleView(BaseModel):
    rule_id: str
    order_index: int
    target_instance_id: str
    enabled: bool


class MappingView(BaseModel):
    mapping_id: str
    instance_id: str
    data_type: str
    direction: str


class ConfigView(BaseModel):
    instances: list[InstanceView] = Field(default_factory=list)
    routing_rules: list[RoutingRuleView] = Field(default_factory=list)
    mappings: list[MappingView] = Field(default_factory=list)


class MappingReport(BaseModel):
    mapping_id: str
    unmapped_required: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ConnectivityResult(BaseModel):
    instance_id: str
    reachable: bool
