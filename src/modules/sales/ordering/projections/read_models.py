"""Order read models.

Two distinct views enforce FR-19 *by construction*:
- `ResellerOrderView` has NO ERP identity (no connection id, no erp order id).
- `OperatorOrderView` includes ERP identity for operator screens only.

Lifecycle is presented with the exact reseller-facing words from the design. Increment 5
adds the two "scores" (fulfillment + invoice) and the delivered fact (box/license),
plus the named parties and the per-line vendor/"scheduled" date — all reseller-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..domain.models import DeliveryStatus, FulfillmentStatus, InvoiceStatus, OrderState

if TYPE_CHECKING:
    from src.shared.money import Money, TaxRate

# Internal state -> reseller-facing lifecycle word. SCREAMING_SNAKE_CASE, consistent with
# fulfillment_status/delivery_status/invoice_status below (previously this table emitted
# Title Case human text — e.g. "Sent to ERP" — while the other three always emitted their
# raw enum value; that mismatch is why this table exists in this form now). Presentation
# (human-friendly label, color) is the UI's job, not the API's — see ui/src/lib/statusLabel.ts.
# ACCEPTED (formerly READY_FOR_DELIVERY) keeps the VALIDATED reseller label (Q2=A); FULFILLED
# is gone.
STATUS_LABELS: dict[OrderState, str] = {
    OrderState.SUBMITTED: "SUBMITTED",
    OrderState.VALIDATED: "VALIDATED",
    OrderState.ACCEPTED: "VALIDATED",
    OrderState.SENT_TO_ERP: "SENT_TO_ERP",
    OrderState.CONFIRMED: "CONFIRMED",
    OrderState.CLOSED: "CLOSED",
    OrderState.REJECTED: "REJECTED",
    OrderState.RETRYING: "RETRYING",
    OrderState.CANCELLED: "CANCELLED",
}


def status_label(state: OrderState) -> str:
    return STATUS_LABELS.get(state, state.value)


@dataclass(frozen=True)
class OrderLineView:
    product_key: str
    quantity: float
    unit_of_measure: str
    line_id: str = ""
    kind: str = "PHYSICAL"
    unit_price: Money | None = None
    line_total: Money | None = None  # computed once at projection time (calculations.line_total)
    tax_rates: list[TaxRate] = field(default_factory=list)  # passthrough, for ERP submission
    line_discount: Money | None = None  # passthrough, for ERP submission
    # Increment 5 fulfillment facts, accumulated by the projector:
    shipped_quantity: float = 0.0
    delivered_quantity: float = 0.0
    invoiced_quantity: float = 0.0
    scheduled_date: str | None = None  # vendor date (FR-E1), None until purchasing sets it


def _aggregate_status(
    lines: list[OrderLineView], recorded: str, none_s: str, partial_s: str, full_s: str
) -> str:
    """Roll per-line recorded quantities up to one of none/partial/full."""
    relevant = [line for line in lines if line.quantity > 0]
    if not relevant:
        return none_s
    got = [getattr(line, recorded) for line in relevant]
    if all(g >= line.quantity for g, line in zip(got, relevant, strict=False)):
        return full_s
    if any(g > 0 for g in got):
        return partial_s
    return none_s


def fulfillment_status(lines: list[OrderLineView]) -> str:
    return _aggregate_status(
        lines,
        "shipped_quantity",
        FulfillmentStatus.UNFULFILLED.value,
        FulfillmentStatus.PARTIALLY_FULFILLED.value,
        FulfillmentStatus.FULFILLED.value,
    )


def delivery_status(lines: list[OrderLineView]) -> str:
    return _aggregate_status(
        lines,
        "delivered_quantity",
        DeliveryStatus.NOT_DELIVERED.value,
        DeliveryStatus.PARTIALLY_DELIVERED.value,
        DeliveryStatus.DELIVERED.value,
    )


def invoice_status(lines: list[OrderLineView]) -> str:
    return _aggregate_status(
        lines,
        "invoiced_quantity",
        InvoiceStatus.NOT_INVOICED.value,
        InvoiceStatus.PARTIALLY_INVOICED.value,
        InvoiceStatus.INVOICED.value,
    )


@dataclass(frozen=True)
class TimelineEntry:
    status: str
    occurred_at: str


@dataclass(frozen=True)
class Parties:
    """Named parties on the order (FR-C). Reseller-safe — no ERP identity."""

    end_customer_name: str = ""
    ship_to: str = ""
    subsidiary_id: str = ""
    quote_id: str = ""


@dataclass(frozen=True)
class ResellerOrderView:
    """Reseller-safe. Intentionally excludes connection id / erp order id (FR-19)."""

    order_id: str
    client_reference: str
    status: str
    lines: list[OrderLineView] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    subtotal: Money | None = None  # sum of priced lines' line_total; None if none priced
    fulfillment_status: str = FulfillmentStatus.UNFULFILLED.value
    delivery_status: str = DeliveryStatus.NOT_DELIVERED.value
    invoice_status: str = InvoiceStatus.NOT_INVOICED.value
    parties: Parties = field(default_factory=Parties)


@dataclass(frozen=True)
class OperatorOrderView:
    """Operator view — may include ERP identity."""

    order_id: str
    tenant_id: str
    client_reference: str
    status: str
    owning_connection_id: str | None
    erp_order_id: str | None
    lines: list[OrderLineView] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    subtotal: Money | None = None
    fulfillment_status: str = FulfillmentStatus.UNFULFILLED.value
    delivery_status: str = DeliveryStatus.NOT_DELIVERED.value
    invoice_status: str = InvoiceStatus.NOT_INVOICED.value
    parties: Parties = field(default_factory=Parties)
