"""Invoice aggregate — a minimal, record-only event-sourced aggregate (one command, one
event). Reuses the generic `EventSourcedRepository` kernel. Split out of `fulfillment`."""

from __future__ import annotations

from typing import Any

from src.shared.eventsourcing import Aggregate

from .events import InvoiceRecorded


class Invoice(Aggregate):
    aggregate_type = "Invoice"

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.order_id: str = ""
        self.lines: list[dict[str, Any]] = []
        self.erp_invoice_id: str | None = None

    @classmethod
    def record(
        cls,
        *,
        invoice_id: str,
        order_id: str,
        lines: list[dict[str, Any]],
        erp_invoice_id: str | None = None,
    ) -> Invoice:
        if not lines:
            raise ValueError("an invoice must have at least one line")
        inv = cls(invoice_id)
        inv.emit(
            InvoiceRecorded(
                invoice_id=invoice_id,
                order_id=order_id,
                lines=lines,
                erp_invoice_id=erp_invoice_id,
            )
        )
        return inv

    def _apply_InvoiceRecorded(self, e: InvoiceRecorded) -> None:
        self.order_id = e.order_id
        self.lines = list(e.lines)
        self.erp_invoice_id = e.erp_invoice_id

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "lines": self.lines,
            "erp_invoice_id": self.erp_invoice_id,
        }

    def restore(self, state: dict[str, Any]) -> None:
        self.order_id = state["order_id"]
        self.lines = state["lines"]
        self.erp_invoice_id = state["erp_invoice_id"]
