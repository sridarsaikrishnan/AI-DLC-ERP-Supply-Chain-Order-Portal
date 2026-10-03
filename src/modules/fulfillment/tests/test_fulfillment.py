from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.fulfillment.application.service import (
    FulfillmentService,
    InvoiceService,
    PaymentService,
    ReturnService,
)
from src.modules.fulfillment.domain.aggregates import Fulfillment, Invoice, Payment, Return
from src.modules.ordering.domain.aggregate import Order
from src.modules.ordering.domain.models import FulfillmentStatus, InvoiceStatus, OrderLine
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.types import ConnectionId, OrderId, TenantId


def _confirmed_order(store: InMemoryEventStore) -> tuple[EventSourcedRepository[Order], str]:
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order)
    order = Order.submit(
        order_id=OrderId("ord_1"),
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-1",
        lines=[OrderLine(product_key="ANVIL", quantity=Decimal(10), unit_of_measure="EA", line_id="l_a")],
    )
    order.validate(ConnectionId("conn_1"))
    order.accept()
    order.send_to_erp("S001")
    order.confirm()
    repo.save(order)
    return repo, "ord_1"


# --- aggregates: pure record-and-replay ---------------------------------------------


def test_fulfillment_records_and_replays() -> None:
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Fulfillment] = EventSourcedRepository(store, Fulfillment)
    f = Fulfillment.record(
        fulfillment_id="fulf_1", order_id="ord_1", lines=[{"product_key": "ANVIL", "quantity": "10"}], carrier="UPS"
    )
    repo.save(f)
    reloaded = repo.get("fulf_1")
    assert reloaded.order_id == "ord_1"
    assert reloaded.carrier == "UPS"
    assert reloaded.lines == [{"product_key": "ANVIL", "quantity": "10"}]


def test_fulfillment_requires_at_least_one_line() -> None:
    with pytest.raises(ValueError):
        Fulfillment.record(fulfillment_id="fulf_2", order_id="ord_1", lines=[])


def test_invoice_records_and_replays() -> None:
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Invoice] = EventSourcedRepository(store, Invoice)
    inv = Invoice.record(invoice_id="inv_1", order_id="ord_1", lines=[{"product_key": "ANVIL", "quantity": "10"}], erp_invoice_id="INV-042")
    repo.save(inv)
    assert repo.get("inv_1").erp_invoice_id == "INV-042"


def test_payment_records_and_replays() -> None:
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Payment] = EventSourcedRepository(store, Payment)
    p = Payment.record(payment_id="pay_1", order_id="ord_1", amount={"amount": "199.90", "currency": "USD"}, method="card")
    repo.save(p)
    reloaded = repo.get("pay_1")
    assert reloaded.amount == {"amount": "199.90", "currency": "USD"}
    assert reloaded.method == "card"


def test_return_records_and_replays() -> None:
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Return] = EventSourcedRepository(store, Return)
    r = Return.record(return_id="ret_1", order_id="ord_1", lines=[{"product_key": "ANVIL", "quantity": "2"}], reason_code="DAMAGED")
    repo.save(r)
    assert repo.get("ret_1").reason_code == "DAMAGED"


# --- coordinating services: the Fulfillment/Invoice -> Order link -------------------


def test_fulfillment_service_updates_order_derived_status() -> None:
    event_store = InMemoryEventStore()
    order_repo, order_id = _confirmed_order(event_store)
    fulfillment_repo: EventSourcedRepository[Fulfillment] = EventSourcedRepository(InMemoryEventStore(), Fulfillment)
    service = FulfillmentService(fulfillment_repo, order_repo)

    service.record(order_id=order_id, lines=[{"line_id": "l_a", "quantity": "10"}], carrier="UPS")

    order = order_repo.get(order_id)
    assert order.fulfillment_status is FulfillmentStatus.FULFILLED
    assert order.state.value == "CONFIRMED"  # order lifecycle itself untouched


def test_invoice_service_updates_order_derived_status() -> None:
    event_store = InMemoryEventStore()
    order_repo, order_id = _confirmed_order(event_store)
    invoice_repo: EventSourcedRepository[Invoice] = EventSourcedRepository(InMemoryEventStore(), Invoice)
    service = InvoiceService(invoice_repo, order_repo)

    service.record(order_id=order_id, lines=[{"line_id": "l_a", "quantity": "4"}])

    order = order_repo.get(order_id)
    assert order.invoice_status is InvoiceStatus.PARTIALLY_INVOICED


def test_payment_service_records_without_touching_order() -> None:
    payment_repo: EventSourcedRepository[Payment] = EventSourcedRepository(InMemoryEventStore(), Payment)
    service = PaymentService(payment_repo)
    payment = service.record(order_id="ord_1", amount={"amount": "50.00", "currency": "USD"}, method="card")
    assert payment.order_id == "ord_1"


def test_return_service_records_without_touching_order() -> None:
    return_repo: EventSourcedRepository[Return] = EventSourcedRepository(InMemoryEventStore(), Return)
    service = ReturnService(return_repo)
    ret = service.record(order_id="ord_1", lines=[{"product_key": "ANVIL", "quantity": "1"}], reason_code="WRONG_ITEM")
    assert ret.order_id == "ord_1"
