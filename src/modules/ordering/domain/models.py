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


@dataclass(frozen=True)
class OrderLine:
    product_key: str
    quantity: Decimal
    unit_of_measure: str
    # Pricing is optional — nothing populates it yet (no catalog price lookup wired in),
    # but the shape exists so calculations.py and event storage are ready for when it is.
    unit_price: Money | None = None
    line_discount: Money | None = None
    tax_rates: list[TaxRate] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.quantity, Decimal):
            # str(x) first, not Decimal(x) directly — Decimal(2.1) picks up float's binary
            # repr artifacts (Decimal('2.100000000000000088817841970012523233890533447265625')),
            # Decimal(str(2.1)) doesn't.
            object.__setattr__(self, "quantity", Decimal(str(self.quantity)))

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe form for an event/snapshot payload (JSONB can't hold Decimal)."""
        return {
            "product_key": self.product_key,
            "quantity": str(self.quantity),
            "unit_of_measure": self.unit_of_measure,
            "unit_price": money_to_payload(self.unit_price),
            "line_discount": money_to_payload(self.line_discount),
            "tax_rates": [tax_rate_to_payload(t) for t in self.tax_rates],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OrderLine":
        return cls(
            product_key=data["product_key"],
            quantity=data["quantity"],
            unit_of_measure=data.get("unit_of_measure", ""),
            unit_price=money_from_payload(data.get("unit_price")),
            line_discount=money_from_payload(data.get("line_discount")),
            tax_rates=[tax_rate_from_payload(t) for t in data.get("tax_rates", [])],
        )


class OrderState(str, Enum):
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY"
    SENT_TO_ERP = "SENT_TO_ERP"
    CONFIRMED = "CONFIRMED"
    FULFILLED = "FULFILLED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


# States from which no further reseller-visible transition happens.
TERMINAL_STATES = frozenset({OrderState.CLOSED, OrderState.CANCELLED, OrderState.REJECTED})
