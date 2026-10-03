"""InvoiceService — records an invoice and, in the same transaction, bumps the order's
invoiced-quantity score (FR-A4). On Postgres both appends share one session via the
injected `UnitOfWork`; in memory it's a no-op. Lines are keyed by `line_id` (FR-A3).

Commit 1 keeps the synchronous Invoice -> Order coupling unchanged from the former
`fulfillment` module; the event-driven saga (ordering consumes `InvoiceRecorded`) lands
in commit 2.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from src.shared.types import generate_id
from src.shared.unit_of_work import NullUnitOfWork, UnitOfWork

from ..domain.aggregate import Invoice

if TYPE_CHECKING:
    from src.modules.sales.ordering.domain.aggregate import Order
    from src.shared.eventsourcing import EventSourcedRepository


def _line_id(line: dict[str, Any]) -> str:
    return str(line.get("line_id") or line.get("product_key") or "")


class InvoiceService:
    def __init__(
        self,
        invoices: EventSourcedRepository[Invoice],
        orders: EventSourcedRepository[Order],
        uow: UnitOfWork | None = None,
    ) -> None:
        self._invoices = invoices
        self._orders = orders
        self._uow = uow or NullUnitOfWork()

    def record(
        self, *, order_id: str, lines: list[dict[str, Any]], erp_invoice_id: str | None = None
    ) -> Invoice:
        invoice = Invoice.record(
            invoice_id=generate_id("inv"),
            order_id=order_id,
            lines=lines,
            erp_invoice_id=erp_invoice_id,
        )
        with self._uow.atomic():
            self._invoices.save(invoice)
            order = self._orders.get(order_id)
            for line in lines:
                order.record_invoice(_line_id(line), Decimal(str(line["quantity"])))
            self._orders.save(order)
        return invoice
