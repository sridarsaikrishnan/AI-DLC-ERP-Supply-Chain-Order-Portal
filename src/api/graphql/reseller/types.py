"""Reseller GraphQL types — reseller-safe ONLY (no ERP identity, FR-19 by construction)."""

from __future__ import annotations

import strawberry


@strawberry.type
class MoneyType:
    amount: float
    currency: str


@strawberry.type
class OrderLineType:
    product_key: str
    quantity: float
    unit_of_measure: str
    unit_price: MoneyType | None
    line_total: MoneyType | None


@strawberry.type
class TimelineEntryType:
    status: str
    occurred_at: str


@strawberry.type
class ResellerOrder:
    order_id: str
    client_reference: str
    status: str
    lines: list[OrderLineType]
    timeline: list[TimelineEntryType]
    subtotal: MoneyType | None


@strawberry.input
class OrderLineInput:
    product_key: str
    quantity: float
    unit_of_measure: str


@strawberry.type
class WebhookEndpointType:
    endpoint_id: str
    name: str
    url: str
    event_types: list[str] | None  # null = subscribed to every dispatchable event
    is_active: bool


@strawberry.type
class WebhookEndpointCreatedType:
    """`signing_secret` is returned ONCE, on creation only — see WebhookEndpointService."""

    endpoint: WebhookEndpointType
    signing_secret: str


@strawberry.type
class WebhookDeliveryType:
    delivery_id: str
    endpoint_id: str
    order_id: str
    event_type: str
    occurred_at: str
    status: str
    attempts: int
    last_response: str | None
    payload: strawberry.scalars.JSON
