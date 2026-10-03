"""Order read models.

Two distinct views enforce FR-19 *by construction*:
- `ResellerOrderView` has NO ERP identity (no connection id, no erp order id).
- `OperatorOrderView` includes ERP identity for operator screens only.

Lifecycle is presented with the exact reseller-facing words from the design.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.shared.money import Money

from ..domain.models import OrderState

# Internal state -> reseller-facing lifecycle word (design README).
STATUS_LABELS: dict[OrderState, str] = {
    OrderState.SUBMITTED: "Submitted",
    OrderState.VALIDATED: "Validated",
    OrderState.READY_FOR_DELIVERY: "Validated",
    OrderState.SENT_TO_ERP: "Sent to ERP",
    OrderState.CONFIRMED: "Confirmed",
    OrderState.FULFILLED: "Fulfilled",
    OrderState.CLOSED: "Closed",
    OrderState.REJECTED: "Rejected",
    OrderState.RETRYING: "Retrying",
    OrderState.CANCELLED: "Cancelled",
}


def status_label(state: OrderState) -> str:
    return STATUS_LABELS.get(state, state.value)


@dataclass(frozen=True)
class OrderLineView:
    product_key: str
    quantity: float
    unit_of_measure: str
    unit_price: Money | None = None
    line_total: Money | None = None  # computed once at projection time (calculations.line_total)


@dataclass(frozen=True)
class TimelineEntry:
    status: str
    occurred_at: str


@dataclass(frozen=True)
class ResellerOrderView:
    """Reseller-safe. Intentionally excludes connection id / erp order id (FR-19)."""

    order_id: str
    client_reference: str
    status: str
    lines: list[OrderLineView] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    subtotal: Money | None = None  # sum of priced lines' line_total; None if none priced


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
