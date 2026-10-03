"""Fulfillment/Invoice/Payment/Return aggregates — each a minimal, record-only
event-sourced aggregate (one command, one event, no amendment/cancellation yet). Proves
the event-sourcing kernel generalizes beyond `Order` (it's generic — `EventSourcedRepository`
takes any `Aggregate` subclass) without inventing more than these 4 need today.
"""

from __future__ import annotations

from typing import Any

from src.shared.eventsourcing import Aggregate

from .events import FulfillmentRecorded, InvoiceRecorded, PaymentRecorded, ReturnRecorded


class Fulfillment(Aggregate):
    aggregate_type = "Fulfillment"

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.order_id: str = ""
        self.lines: list[dict[str, Any]] = []
        self.carrier: str | None = None
        self.tracking_number: str | None = None
        self.proof_of_delivery: str | None = None

    @classmethod
    def record(
        cls,
        *,
        fulfillment_id: str,
        order_id: str,
        lines: list[dict[str, Any]],
        carrier: str | None = None,
        tracking_number: str | None = None,
        proof_of_delivery: str | None = None,
    ) -> Fulfillment:
        if not lines:
            raise ValueError("a fulfillment must have at least one line")
        f = cls(fulfillment_id)
        f.emit(
            FulfillmentRecorded(
                fulfillment_id=fulfillment_id, order_id=order_id, lines=lines,
                carrier=carrier, tracking_number=tracking_number, proof_of_delivery=proof_of_delivery,
            )
        )
        return f

    def _apply_FulfillmentRecorded(self, e: FulfillmentRecorded) -> None:
        self.order_id = e.order_id
        self.lines = list(e.lines)
        self.carrier = e.carrier
        self.tracking_number = e.tracking_number
        self.proof_of_delivery = e.proof_of_delivery

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id, "lines": self.lines, "carrier": self.carrier,
            "tracking_number": self.tracking_number, "proof_of_delivery": self.proof_of_delivery,
        }

    def restore(self, state: dict[str, Any]) -> None:
        self.order_id = state["order_id"]
        self.lines = state["lines"]
        self.carrier = state["carrier"]
        self.tracking_number = state["tracking_number"]
        self.proof_of_delivery = state.get("proof_of_delivery")


class Invoice(Aggregate):
    aggregate_type = "Invoice"

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.order_id: str = ""
        self.lines: list[dict[str, Any]] = []
        self.erp_invoice_id: str | None = None

    @classmethod
    def record(cls, *, invoice_id: str, order_id: str, lines: list[dict[str, Any]], erp_invoice_id: str | None = None) -> Invoice:
        if not lines:
            raise ValueError("an invoice must have at least one line")
        inv = cls(invoice_id)
        inv.emit(InvoiceRecorded(invoice_id=invoice_id, order_id=order_id, lines=lines, erp_invoice_id=erp_invoice_id))
        return inv

    def _apply_InvoiceRecorded(self, e: InvoiceRecorded) -> None:
        self.order_id = e.order_id
        self.lines = list(e.lines)
        self.erp_invoice_id = e.erp_invoice_id

    def snapshot_state(self) -> dict[str, Any]:
        return {"order_id": self.order_id, "lines": self.lines, "erp_invoice_id": self.erp_invoice_id}

    def restore(self, state: dict[str, Any]) -> None:
        self.order_id = state["order_id"]
        self.lines = state["lines"]
        self.erp_invoice_id = state["erp_invoice_id"]


class Payment(Aggregate):
    """Standalone record — not yet wired into `Order.invoice_status` (e.g. a `PAID`
    derivation). Deliberately scoped out: that needs a design decision about partial
    payments/overpayment that hasn't been asked for, not an oversight."""

    aggregate_type = "Payment"

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.order_id: str = ""
        self.invoice_id: str | None = None
        self.amount: dict[str, str] = {}
        self.method: str = ""

    @classmethod
    def record(cls, *, payment_id: str, order_id: str, amount: dict[str, str], method: str, invoice_id: str | None = None) -> Payment:
        p = cls(payment_id)
        p.emit(PaymentRecorded(payment_id=payment_id, order_id=order_id, invoice_id=invoice_id, amount=amount, method=method))
        return p

    def _apply_PaymentRecorded(self, e: PaymentRecorded) -> None:
        self.order_id = e.order_id
        self.invoice_id = e.invoice_id
        self.amount = dict(e.amount)
        self.method = e.method

    def snapshot_state(self) -> dict[str, Any]:
        return {"order_id": self.order_id, "invoice_id": self.invoice_id, "amount": self.amount, "method": self.method}

    def restore(self, state: dict[str, Any]) -> None:
        self.order_id = state["order_id"]
        self.invoice_id = state["invoice_id"]
        self.amount = state["amount"]
        self.method = state["method"]


class Return(Aggregate):
    """Standalone record — not yet wired into `Order.fulfillment_status` (reversing
    `fulfilled_qty_by_line`). Deliberately scoped out: whether a return should reopen
    fulfillment status is a real business-policy question, not answered here."""

    aggregate_type = "Return"

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.order_id: str = ""
        self.lines: list[dict[str, Any]] = []
        self.reason_code: str = ""

    @classmethod
    def record(cls, *, return_id: str, order_id: str, lines: list[dict[str, Any]], reason_code: str) -> Return:
        if not lines:
            raise ValueError("a return must have at least one line")
        r = cls(return_id)
        r.emit(ReturnRecorded(return_id=return_id, order_id=order_id, lines=lines, reason_code=reason_code))
        return r

    def _apply_ReturnRecorded(self, e: ReturnRecorded) -> None:
        self.order_id = e.order_id
        self.lines = list(e.lines)
        self.reason_code = e.reason_code

    def snapshot_state(self) -> dict[str, Any]:
        return {"order_id": self.order_id, "lines": self.lines, "reason_code": self.reason_code}

    def restore(self, state: dict[str, Any]) -> None:
        self.order_id = state["order_id"]
        self.lines = state["lines"]
        self.reason_code = state["reason_code"]
