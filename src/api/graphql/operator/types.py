"""Operator GraphQL types — may include ERP identity (operator screens only)."""

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
class OperatorOrderLineType:
    product_key: str
    quantity: float
    unit_of_measure: str
    line_id: str
    kind: str
    unit_price: MoneyType | None
    line_total: MoneyType | None
    shipped_quantity: float
    delivered_quantity: float
    invoiced_quantity: float
    scheduled_date: str | None


@strawberry.type
class OperatorTimelineEntryType:
    status: str
    occurred_at: str


@strawberry.type
class OperatorPartiesType:
    end_customer_name: str
    ship_to: str
    operating_company_id: str
    quote_id: str


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
    subtotal: MoneyType | None
    fulfillment_status: str  # UNFULFILLED | PARTIALLY_FULFILLED | FULFILLED (ADR-0014)
    delivery_status: str  # NOT_DELIVERED | PARTIALLY_DELIVERED | DELIVERED (FR-D3)
    invoice_status: str  # NOT_INVOICED | PARTIALLY_INVOICED | INVOICED
    parties: OperatorPartiesType


@strawberry.type
class ShipmentType:
    shipment_id: str
    order_id: str
    carrier: str | None
    tracking_number: str | None
    proof_of_delivery: str | None


@strawberry.type
class InvoiceType:
    invoice_id: str
    order_id: str
    erp_invoice_id: str | None


@strawberry.type
class PaymentType:
    payment_id: str
    order_id: str
    amount: MoneyType
    method: str


@strawberry.type
class ReturnType:
    return_id: str
    order_id: str
    reason_code: str


@strawberry.input
class LineQuantityInput:
    """A line reference plus a quantity — shared by record_shipment / record_invoice /
    record_return (each records a per-line quantity against an order)."""

    line_id: str
    quantity: float


@strawberry.type
class ConnectionType:
    connection_id: str
    erp_type: str
    instance_label: str
    base_url: str
    credentials: strawberry.scalars.JSON  # generic non-secret params — never the secret itself
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
    """Catalog item — identity only now (Increment 5, ADR-0016). Price/tax/discount moved
    to the quote; `kind` says box vs. license."""

    item_id: str
    sku: str
    name: str
    owning_connection_id: str
    kind: str


@strawberry.type
class OperatingCompanyType:
    operating_company_id: str
    name: str
    country: str
    language: str


@strawberry.type
class QuoteLineType:
    product_key: str
    unit_price: MoneyType
    unit_of_measure: str
    tax_code: str | None
    tax_rate: float | None
    line_discount: MoneyType | None


@strawberry.type
class QuoteType:
    quote_id: str
    tenant_id: str
    operating_company_id: str
    end_customer_name: str
    ship_to: str
    currency: str
    valid_from: str
    valid_until: str
    status: str
    lines: list[QuoteLineType]


@strawberry.input
class QuoteLineInput:
    product_key: str
    unit_price: float
    unit_of_measure: str = ""
    tax_code: str | None = None
    tax_rate: float | None = None
    tax_inclusive: bool = False
    line_discount: float | None = None


@strawberry.type
class OrderEventType:
    """The raw event stream for one order — the developer/event-sourcing view. Not a
    projection: this is exactly what's in the `events` table, in order."""

    event_type: str
    version: int
    occurred_at: str
    correlation_id: str | None
    payload: strawberry.scalars.JSON
