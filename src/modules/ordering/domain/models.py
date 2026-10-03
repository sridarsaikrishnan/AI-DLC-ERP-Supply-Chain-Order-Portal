"""Order value objects and lifecycle states."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from src.shared.money import (
    Money,
    TaxRate,
    money_from_payload,
    money_to_payload,
    tax_rate_from_payload,
    tax_rate_to_payload,
)

# Line kind, carried on the order line as a plain string (not the catalog's `ItemKind`
# enum — ordering must not import catalog's domain). Copied from the catalog at placement.
KIND_PHYSICAL = "PHYSICAL"
KIND_LICENSE = "LICENSE"


def line_is_delivered(kind: str, carrier: str | None, proof_of_delivery: str | None) -> bool:
    """The one place the delivered rule lives (FR-D2), shared by the aggregate and the
    projection so they can't drift: a license is delivered the moment it ships; a box
    (physical) is delivered only once a carrier or proof-of-delivery is recorded."""
    return kind == KIND_LICENSE or bool(carrier) or bool(proof_of_delivery)


@dataclass(frozen=True)
class OrderLine:
    product_key: str
    quantity: Decimal
    unit_of_measure: str
    # Each line carries its own id (Increment 5, FR-A3): generated at placement, stable
    # across event replay, and the key fulfillment/invoice/vendor records attach to —
    # so two lines of the same SKU are tracked separately.
    line_id: str = ""
    # "box" (PHYSICAL) or "license" (LICENSE) — copied from the catalog item at placement
    # (Increment 5, FR-D1). Drives the delivered fact (FR-D2).
    kind: str = KIND_PHYSICAL
    # Pricing is copied from the Quote at placement (Increment 5, FR-B3 / ADR-0016).
    unit_price: Money | None = None
    line_discount: Money | None = None
    tax_rates: list[TaxRate] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.quantity, Decimal):
            # str(x) first, not Decimal(x) directly — Decimal(2.1) picks up float's binary
            # repr artifacts (Decimal('2.100000000000000088817841970012523233890533447265625')),
            # Decimal(str(2.1)) doesn't.
            object.__setattr__(self, "quantity", Decimal(str(self.quantity)))

    @property
    def is_license(self) -> bool:
        return self.kind == KIND_LICENSE

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe form for an event/snapshot payload (JSONB can't hold Decimal)."""
        return {
            "product_key": self.product_key,
            "quantity": str(self.quantity),
            "unit_of_measure": self.unit_of_measure,
            "line_id": self.line_id,
            "kind": self.kind,
            "unit_price": money_to_payload(self.unit_price),
            "line_discount": money_to_payload(self.line_discount),
            "tax_rates": [tax_rate_to_payload(t) for t in self.tax_rates],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrderLine:
        # Legacy orders (pre-Increment-5) stored no line_id/kind — fall back so their
        # events still replay: line_id defaults to product_key (how tracking keyed before),
        # kind defaults to PHYSICAL.
        return cls(
            product_key=data["product_key"],
            quantity=data["quantity"],
            unit_of_measure=data.get("unit_of_measure", ""),
            line_id=data.get("line_id") or data["product_key"],
            kind=data.get("kind") or KIND_PHYSICAL,
            unit_price=money_from_payload(data.get("unit_price")),
            line_discount=money_from_payload(data.get("line_discount")),
            tax_rates=[tax_rate_from_payload(t) for t in data.get("tax_rates", [])],
        )


class OrderState(str, Enum):
    """The order lifecycle. Increment 5: `READY_FOR_DELIVERY` was renamed `ACCEPTED`
    (Q2=A) — it means "routed, ready to send to the ERP", which collided with the literal
    "delivery" of box/license fulfillment — and `FULFILLED` was removed from the lifecycle
    entirely (Q3=A): fulfilled/shipped/delivered are now the orthogonal score + facts
    (see `FulfillmentStatus`/`DeliveryStatus`), not a lifecycle step."""

    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    ACCEPTED = "ACCEPTED"
    SENT_TO_ERP = "SENT_TO_ERP"
    CONFIRMED = "CONFIRMED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


# States from which no further reseller-visible transition happens.
TERMINAL_STATES = frozenset({OrderState.CLOSED, OrderState.CANCELLED, OrderState.REJECTED})


class FulfillmentStatus(str, Enum):
    """The shipped-quantity "score" — derived from `shipped_qty_by_line` vs ordered
    quantities, orthogonal to `OrderState` (ADR-0014). `FULFILLED` lives here now and only
    here (Increment 5, FR-A6). `UNFULFILLED` is the correct default, not a fault."""

    UNFULFILLED = "UNFULFILLED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FULFILLED = "FULFILLED"


class DeliveryStatus(str, Enum):
    """The delivered fact (Increment 5, FR-D2/D3) — derived from `delivered_qty_by_line`.
    Distinct from `FulfillmentStatus`: a physical line is shipped but not delivered until a
    carrier or proof-of-delivery is recorded; a license is delivered the moment it ships."""

    NOT_DELIVERED = "NOT_DELIVERED"
    PARTIALLY_DELIVERED = "PARTIALLY_DELIVERED"
    DELIVERED = "DELIVERED"


class InvoiceStatus(str, Enum):
    """The invoiced "score" — derived from `invoiced_qty_by_line`. Does not yet derive
    `PAID` (ADR-0014) — that needs `Payment` records wired in, deliberately not done yet."""

    NOT_INVOICED = "NOT_INVOICED"
    PARTIALLY_INVOICED = "PARTIALLY_INVOICED"
    INVOICED = "INVOICED"
