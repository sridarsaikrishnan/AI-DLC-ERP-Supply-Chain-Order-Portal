"""PaymentService — records a payment. Standalone: not wired into `Order.invoice_status`
yet (see `Payment`'s own docstring for why), so no order repository or UnitOfWork."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.shared.types import generate_id

from ..domain.aggregate import Payment

if TYPE_CHECKING:
    from src.shared.eventsourcing import EventSourcedRepository


class PaymentService:
    def __init__(self, payments: EventSourcedRepository[Payment]) -> None:
        self._payments = payments

    def record(
        self, *, order_id: str, amount: dict[str, str], method: str, invoice_id: str | None = None
    ) -> Payment:
        payment = Payment.record(
            payment_id=generate_id("pay"),
            order_id=order_id,
            amount=amount,
            method=method,
            invoice_id=invoice_id,
        )
        self._payments.save(payment)
        return payment
