"""InvoiceService — records an invoice and nothing else.

The invoice's `InvoiceRecorded` event is published; the order's invoiced-quantity score is
bumped asynchronously by the ordering saga consumer that reacts to that event (ADR-0018),
not by this service reaching into the Order aggregate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.shared.eventsourcing.errors import AggregateNotFound
from src.shared.types import generate_id

from ..domain.aggregate import Invoice

if TYPE_CHECKING:
    from src.shared.eventsourcing import EventSourcedRepository


class InvoiceService:
    def __init__(self, invoices: EventSourcedRepository[Invoice]) -> None:
        self._invoices = invoices

    def record(
        self,
        *,
        order_id: str,
        lines: list[dict[str, Any]],
        erp_invoice_id: str | None = None,
        tenant_id: str = "",
    ) -> Invoice:
        invoice = Invoice.record(
            invoice_id=generate_id("inv"),
            order_id=order_id,
            lines=lines,
            erp_invoice_id=erp_invoice_id,
            tenant_id=tenant_id,
        )
        self._invoices.save(invoice)
        return invoice

    def record_once(
        self,
        *,
        invoice_id: str,
        order_id: str,
        lines: list[dict[str, Any]],
        erp_invoice_id: str | None = None,
        tenant_id: str = "",
    ) -> Invoice | None:
        """Record an ERP invoice the first time we see its id. A later poll is a no-op."""
        try:
            self._invoices.get(invoice_id)
        except AggregateNotFound:
            pass
        else:
            return None
        invoice = Invoice.record(
            invoice_id=invoice_id,
            order_id=order_id,
            lines=lines,
            erp_invoice_id=erp_invoice_id,
            tenant_id=tenant_id,
        )
        self._invoices.save(invoice)
        return invoice
