"""Payment aggregate — a minimal, record-only event-sourced aggregate. Split out of
`fulfillment`.

Standalone record — not yet wired into `Order.invoice_status` (e.g. a `PAID` derivation).
Deliberately scoped out: that needs a design decision about partial payments/overpayment
that hasn't been asked for, not an oversight.
"""

from __future__ import annotations

from typing import Any

from src.shared.eventsourcing import Aggregate

from .events import PaymentRecorded


class Payment(Aggregate):
    aggregate_type = "Payment"

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.order_id: str = ""
        self.invoice_id: str | None = None
        self.amount: dict[str, str] = {}
        self.method: str = ""

    @classmethod
    def record(
        cls,
        *,
        payment_id: str,
        order_id: str,
        amount: dict[str, str],
        method: str,
        invoice_id: str | None = None,
    ) -> Payment:
        p = cls(payment_id)
        p.emit(
            PaymentRecorded(
                payment_id=payment_id,
                order_id=order_id,
                invoice_id=invoice_id,
                amount=amount,
                method=method,
            )
        )
        return p

    def _apply_PaymentRecorded(self, e: PaymentRecorded) -> None:
        self.order_id = e.order_id
        self.invoice_id = e.invoice_id
        self.amount = dict(e.amount)
        self.method = e.method

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "invoice_id": self.invoice_id,
            "amount": self.amount,
            "method": self.method,
        }

    def restore(self, state: dict[str, Any]) -> None:
        self.order_id = state["order_id"]
        self.invoice_id = state["invoice_id"]
        self.amount = state["amount"]
        self.method = state["method"]
