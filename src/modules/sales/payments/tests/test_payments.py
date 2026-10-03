from __future__ import annotations

from src.modules.sales.payments.application.service import PaymentService
from src.modules.sales.payments.domain.aggregate import Payment
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore


def test_payment_records_and_replays() -> None:
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Payment] = EventSourcedRepository(store, Payment)
    p = Payment.record(
        payment_id="pay_1",
        order_id="ord_1",
        amount={"amount": "199.90", "currency": "USD"},
        method="card",
    )
    repo.save(p)
    reloaded = repo.get("pay_1")
    assert reloaded.amount == {"amount": "199.90", "currency": "USD"}
    assert reloaded.method == "card"


def test_payment_service_records_without_touching_order() -> None:
    payment_repo: EventSourcedRepository[Payment] = EventSourcedRepository(
        InMemoryEventStore(), Payment
    )
    service = PaymentService(payment_repo)
    payment = service.record(
        order_id="ord_1", amount={"amount": "50.00", "currency": "USD"}, method="card"
    )
    assert payment.order_id == "ord_1"
