"""U2 API DTOs (LC-U2-3)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from ..foundation.canonical.models import Address, CanonicalOrderLine


class PlaceOrderRequest(BaseModel):
    client_reference: str
    order_date: date
    ship_to: Address
    currency: str
    notes: str | None = None
    line_items: list[CanonicalOrderLine] = Field(default_factory=list)


class AmendRequest(BaseModel):
    client_reference: str
    order_date: date
    ship_to: Address
    currency: str
    notes: str | None = None
    line_items: list[CanonicalOrderLine] = Field(default_factory=list)


class OrderAck(BaseModel):
    order_id: str
    lifecycle_state: str


class OrderView(BaseModel):
    order_id: str
    client_reference: str
    lifecycle_state: str
    erp_reference: str | None = None
    created_at: datetime | None = None


class StatusEntry(BaseModel):
    state: str
    reason: str | None = None
    occurred_at: datetime


class StatusHistoryView(BaseModel):
    order_id: str
    history: list[StatusEntry] = Field(default_factory=list)


class ProductView(BaseModel):
    product_key: str
    name: str
    description: str | None = None


class InventoryView(BaseModel):
    product_key: str
    available_quantity: float
    unit_of_measure: str


class ActionAck(BaseModel):
    order_id: str
    accepted: bool = True
