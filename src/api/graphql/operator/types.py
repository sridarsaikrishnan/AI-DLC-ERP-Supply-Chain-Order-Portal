"""Operator GraphQL types — may include ERP identity (operator screens only)."""

from __future__ import annotations

import strawberry


@strawberry.type
class OperatorOrderLineType:
    product_key: str
    quantity: float
    unit_of_measure: str


@strawberry.type
class OperatorTimelineEntryType:
    status: str
    occurred_at: str


@strawberry.type
class OperatorOrder:
    order_id: str
    tenant_id: str
    client_reference: str
    status: str
    owning_connection_id: str | None
    erp_order_id: str | None
    lines: list[OperatorOrderLineType]
    timeline: list[OperatorTimelineEntryType]


@strawberry.type
class ConnectionType:
    connection_id: str
    erp_type: str
    instance_label: str
    base_url: str
    database: str
    username: str
    status: str
    secret_ref: str
    has_webhook_secret: bool


@strawberry.type
class BindingType:
    binding_id: str
    tenant_id: str
    connection_id: str
    erp_customer_id: str
    status: str


@strawberry.type
class ItemType:
    item_id: str
    sku: str
    name: str
    owning_connection_id: str


@strawberry.type
class OrderEventType:
    """The raw event stream for one order — the developer/event-sourcing view. Not a
    projection: this is exactly what's in the `events` table, in order."""

    event_type: str
    version: int
    occurred_at: str
    correlation_id: str | None
    payload: strawberry.scalars.JSON
