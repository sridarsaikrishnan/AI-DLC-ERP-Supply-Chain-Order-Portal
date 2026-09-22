"""Canonical (ERP-agnostic) domain models (LC-5).

These schemas are the contract between the client-facing modules and the
integration module. Product identity uses a portal-side product key (Q2=A);
native ERP ids live in the mapping layer, not here.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class LifecycleState(str, Enum):
    SUBMITTED = "Submitted"
    ACCEPTED = "Accepted"
    PROCESSING = "Processing"
    SHIPPED = "Shipped"
    INVOICED = "Invoiced"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    AMENDED = "Amended"


class Address(BaseModel):
    name: str
    lines: list[str] = Field(default_factory=list)
    city: str
    region: str | None = None
    postal_code: str | None = None
    country: str


class CanonicalOrderLine(BaseModel):
    line_id: str | None = None
    product_key: str
    quantity: float
    unit_of_measure: str
    requested_date: date | None = None


class CanonicalSalesOrder(BaseModel):
    order_id: str | None = None
    tenant_id: str
    client_reference: str
    order_date: date
    ship_to: Address
    currency: str
    notes: str | None = None
    line_items: list[CanonicalOrderLine] = Field(default_factory=list)
    lifecycle_state: LifecycleState = LifecycleState.SUBMITTED


class CanonicalOrderStatus(BaseModel):
    order_id: str
    state: LifecycleState
    erp_reference: str | None = None
    reason: str | None = None
    occurred_at: datetime


class CanonicalProduct(BaseModel):
    product_key: str
    name: str
    description: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


class CanonicalInventory(BaseModel):
    product_key: str
    available_quantity: float
    unit_of_measure: str
    as_of: datetime
    instance_id: str | None = None
