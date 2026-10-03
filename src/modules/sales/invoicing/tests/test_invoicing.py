from __future__ import annotations

from decimal import Decimal

from src.modules.sales.invoicing.application.service import InvoiceService
from src.modules.sales.invoicing.domain.aggregate import Invoice
from src.modules.sales.ordering.application.fulfillment_consumer import OrderFulfillmentConsumer
from src.modules.sales.ordering.domain.aggregate import Order
from src.modules.sales.ordering.domain.models import InvoiceStatus, OrderLine
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.messaging import InMemoryMessageBus
from src.shared.types import ConnectionId, OrderId, TenantId


def _confirmed_order(store: InMemoryEventStore) -> tuple[EventSourcedRepository[Order], str]:
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order)
    order = Order.submit(
        order_id=OrderId("ord_1"),
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-1",
        lines=[
            OrderLine(
                product_key="ANVIL", quantity=Decimal(10), unit_of_measure="EA", line_id="l_a"
            )
        ],
    )
    order.validate(ConnectionId("conn_1"))
    order.accept()
    order.send_to_erp("S001")
    order.confirm()
    repo.save(order)
    return repo, "ord_1"


def test_invoice_records_and_replays() -> None:
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Invoice] = EventSourcedRepository(store, Invoice)
    inv = Invoice.record(
        invoice_id="inv_1",
        order_id="ord_1",
        lines=[{"product_key": "ANVIL", "quantity": "10"}],
        erp_invoice_id="INV-042",
    )
    repo.save(inv)
    assert repo.get("inv_1").erp_invoice_id == "INV-042"


def test_invoice_service_records_without_touching_an_order() -> None:
    invoice_repo: EventSourcedRepository[Invoice] = EventSourcedRepository(
        InMemoryEventStore(), Invoice
    )
    invoice = InvoiceService(invoice_repo).record(
        order_id="ord_1", lines=[{"line_id": "l_a", "quantity": "4"}], erp_invoice_id="INV-042"
    )
    assert invoice.order_id == "ord_1"
    assert invoice_repo.get(invoice.id).erp_invoice_id == "INV-042"


def test_recording_an_invoice_updates_the_order_via_the_saga() -> None:
    store = InMemoryEventStore()
    order_repo, order_id = _confirmed_order(store)

    bus = InMemoryMessageBus()
    bus.subscribe(
        "order-fulfillment",
        OrderFulfillmentConsumer(order_repo).handle,
        event_types={"ShipmentRecorded", "InvoiceRecorded"},
    )
    invoice_repo: EventSourcedRepository[Invoice] = EventSourcedRepository(
        InMemoryEventStore(), Invoice, publisher=bus
    )
    InvoiceService(invoice_repo).record(
        order_id=order_id, lines=[{"line_id": "l_a", "quantity": "4"}]
    )
    bus.run_until_empty()

    assert order_repo.get(order_id).invoice_status is InvoiceStatus.PARTIALLY_INVOICED
