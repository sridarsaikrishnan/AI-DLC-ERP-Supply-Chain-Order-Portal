"""Configuration domain models (owned by U0; authored by U4, consumed by U3).

Routing rules use structured condition clauses (Q6=A). Mapping uses a hybrid of
structured field entries plus optional text expressions (Q5=C).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ErpType(str, Enum):
    ERP_NEXT = "ERP_NEXT"
    ODOO = "ODOO"


class DataType(str, Enum):
    SALES_ORDER = "SALES_ORDER"
    ORDER_STATUS = "ORDER_STATUS"
    PRODUCT = "PRODUCT"
    INVENTORY = "INVENTORY"


class Direction(str, Enum):
    TO_ERP = "TO_ERP"
    FROM_ERP = "FROM_ERP"


class ConditionOperator(str, Enum):
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    IN = "IN"
    CONTAINS = "CONTAINS"
    GT = "GT"
    LT = "LT"


class ErpInstance(BaseModel):
    instance_id: str
    erp_type: ErpType
    display_name: str
    connection_ref: str  # reference/handle; see NFR-U0-SEC-2 (inline creds accepted per Q7=A)
    status: str = "active"


class RoutingCondition(BaseModel):
    field: str
    operator: ConditionOperator
    value: object


class RoutingRule(BaseModel):
    rule_id: str
    order_index: int
    conditions: list[RoutingCondition] = Field(default_factory=list)  # ANDed
    target_instance_id: str
    enabled: bool = True


class MappingEntry(BaseModel):
    source_path: str
    target_path: str
    value_map: dict[str, str] | None = None


class MappingExpression(BaseModel):
    target_path: str
    expression: str


class MappingDefinition(BaseModel):
    mapping_id: str
    instance_id: str
    data_type: DataType
    direction: Direction
    field_entries: list[MappingEntry] = Field(default_factory=list)
    expressions: list[MappingExpression] = Field(default_factory=list)
