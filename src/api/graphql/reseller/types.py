"""Reseller GraphQL types — reseller-safe ONLY (no ERP identity, FR-19 by construction)."""

from __future__ import annotations

import strawberry


@strawberry.type
class MoneyType:
    # str, not float (known gap, architect review 2026-10-04): internal Money/TaxRate
    # are Decimal-exact; float can't represent 19.99 exactly, and a client doing its own
    # arithmetic on this field would inherit that error even though every computation
    # inside the platform stays exact end to end.
    amount: str
    currency: str


@strawberry.type
class OrderLineType:
    product_key: str
    quantity: float
    unit_of_measure: str
    line_id: str
    kind: str  # "PHYSICAL" (box) or "LICENSE"
    unit_price: MoneyType | None
    line_total: MoneyType | None
    shipped_quantity: float
    delivered_quantity: float
    invoiced_quantity: float
    scheduled_date: str | None  # vendor date (FR-E1): what "scheduled" means


@strawberry.type
class TimelineEntryType:
    status: str
    occurred_at: str


@strawberry.type
class PartiesType:
    end_customer_name: str
    ship_to: str
    subsidiary_id: str
    quote_id: str


@strawberry.type
class ResellerOrder:
    order_id: str
    client_reference: str
    status: str
    lines: list[OrderLineType]
    timeline: list[TimelineEntryType]
    subtotal: MoneyType | None
    # The two scores (FR-A5) plus the delivered fact (FR-D3), distinct from shipped.
    fulfillment_status: str
    delivery_status: str
    invoice_status: str
    parties: PartiesType


@strawberry.input
class OrderLineInput:
    """A line of a reply to a quote: a SKU + quantity. No price, no unit of measure — both
    come from the quote (FR-B3 / ADR-0016)."""

    product_key: str
    quantity: float


@strawberry.type
class QuoteLineType:
    product_key: str
    name: str
    kind: str
    unit_price: MoneyType
    unit_of_measure: str


@strawberry.type
class QuoteType:
    """A quote as the reseller sees it — reseller-safe: items, prices, how long they hold,
    and where the goods go. No ERP identity."""

    quote_id: str
    subsidiary_id: str
    end_customer_name: str
    ship_to: str
    currency: str
    valid_from: str
    valid_until: str
    status: str
    lines: list[QuoteLineType]


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
