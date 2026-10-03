"""Coordinating services — each creates/saves its own aggregate, then (for Fulfillment/
Invoice) also updates the `Order` aggregate's derived facts.

Increment 5 (FR-A4): the Fulfillment/Invoice save AND the Order quantity update commit in
one transaction via the injected `UnitOfWork` — on Postgres both appends share one
session; in memory it's a no-op (the in-memory store can't partially fail). This closes
the old window where a crash between the two separate saves left a shipment with no
quantity bump (or the reverse). Lines are keyed by `line_id` now (FR-A3).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.modules.ordering.domain.aggregate import Order
from src.shared.eventsourcing import EventSourcedRepository
from src.shared.types import generate_id
from src.shared.unit_of_work import NullUnitOfWork, UnitOfWork

from ..domain.aggregates import Fulfillment, Invoice, Payment, Return


def _line_id(line: dict[str, Any]) -> str:
    return str(line.get("line_id") or line.get("product_key") or "")


class FulfillmentService:
    def __init__(
        self,
        fulfillments: EventSourcedRepository[Fulfillment],
        orders: EventSourcedRepository[Order],
        uow: UnitOfWork | None = None,
    ) -> None:
        self._fulfillments = fulfillments
        self._orders = orders
        self._uow = uow or NullUnitOfWork()

    def record(
        self,
        *,
        order_id: str,
        lines: list[dict[str, Any]],
        carrier: str | None = None,
        tracking_number: str | None = None,
        proof_of_delivery: str | None = None,
    ) -> Fulfillment:
        fulfillment = Fulfillment.record(
            fulfillment_id=generate_id("fulf"), order_id=order_id, lines=lines,
            carrier=carrier, tracking_number=tracking_number, proof_of_delivery=proof_of_delivery,
        )
        with self._uow.atomic():
            self._fulfillments.save(fulfillment)
            order = self._orders.get(order_id)
            for line in lines:
                order.record_fulfillment(
                    _line_id(line), Decimal(str(line["quantity"])),
                    carrier=carrier, proof_of_delivery=proof_of_delivery,
                )
            self._orders.save(order)
        return fulfillment


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

    def record(self, *, order_id: str, lines: list[dict[str, Any]], erp_invoice_id: str | None = None) -> Invoice:
        invoice = Invoice.record(invoice_id=generate_id("inv"), order_id=order_id, lines=lines, erp_invoice_id=erp_invoice_id)
        with self._uow.atomic():
            self._invoices.save(invoice)
            order = self._orders.get(order_id)
            for line in lines:
                order.record_invoice(_line_id(line), Decimal(str(line["quantity"])))
            self._orders.save(order)
        return invoice


class PaymentService:
    """Standalone — not wired into `Order.invoice_status` yet (see `Payment`'s own
    docstring for why)."""

    def __init__(self, payments: EventSourcedRepository[Payment]) -> None:
        self._payments = payments

    def record(self, *, order_id: str, amount: dict[str, str], method: str, invoice_id: str | None = None) -> Payment:
        payment = Payment.record(payment_id=generate_id("pay"), order_id=order_id, amount=amount, method=method, invoice_id=invoice_id)
        self._payments.save(payment)
        return payment


class ReturnService:
    """Standalone — not wired into `Order.fulfillment_status` yet (see `Return`'s own
    docstring for why)."""

    def __init__(self, returns: EventSourcedRepository[Return]) -> None:
        self._returns = returns

    def record(self, *, order_id: str, lines: list[dict[str, Any]], reason_code: str) -> Return:
        ret = Return.record(return_id=generate_id("ret"), order_id=order_id, lines=lines, reason_code=reason_code)
        self._returns.save(ret)
        return ret
