from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.sales.ordering.application.fulfillment_consumer import OrderFulfillmentConsumer
from src.modules.sales.ordering.domain.aggregate import Order
from src.modules.sales.ordering.domain.models import FulfillmentStatus, OrderLine
from src.modules.sales.shipment.application.service import ShipmentService
from src.modules.sales.shipment.domain.aggregate import Shipment
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.messaging import InMemoryMessageBus
from src.shared.types import OrderId, TenantId


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
        routed_to_connection_id="conn_1",
    )
    order.validate()
    order.accept()
    order.send_to_erp("S001")
    order.confirm()
    repo.save(order)
    return repo, "ord_1"


# --- aggregate: pure record-and-replay ----------------------------------------------


def test_shipment_records_and_replays() -> None:
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Shipment] = EventSourcedRepository(store, Shipment)
    s = Shipment.record(
        shipment_id="shp_1",
        order_id="ord_1",
        lines=[{"product_key": "ANVIL", "quantity": "10"}],
        carrier="UPS",
    )
    repo.save(s)
    reloaded = repo.get("shp_1")
    assert reloaded.order_id == "ord_1"
    assert reloaded.carrier == "UPS"
    assert reloaded.lines == [{"product_key": "ANVIL", "quantity": "10"}]


def test_shipment_requires_at_least_one_line() -> None:
    with pytest.raises(ValueError):
        Shipment.record(shipment_id="shp_2", order_id="ord_1", lines=[])


# --- service: records a shipment ONLY (no order coupling anymore, ADR-0018) ----------


def test_shipment_service_records_without_touching_an_order() -> None:
    shipment_repo: EventSourcedRepository[Shipment] = EventSourcedRepository(
        InMemoryEventStore(), Shipment
    )
    service = ShipmentService(shipment_repo)
    shipment = service.record(
        order_id="ord_1", lines=[{"line_id": "l_a", "quantity": "10"}], carrier="UPS"
    )
    assert shipment.order_id == "ord_1"
    assert shipment_repo.get(shipment.id).carrier == "UPS"


# --- saga: recording a shipment eventually bumps the order's score via events --------


def test_recording_a_shipment_updates_the_order_via_the_saga() -> None:
    store = InMemoryEventStore()
    order_repo, order_id = _confirmed_order(store)

    bus = InMemoryMessageBus()
    bus.subscribe(
        "order-fulfillment",
        OrderFulfillmentConsumer(order_repo).handle,
        event_types={"ShipmentRecorded", "InvoiceRecorded"},
    )
    # Shipment publishes its event; the ordering consumer reacts — no shared transaction.
    shipment_repo: EventSourcedRepository[Shipment] = EventSourcedRepository(
        InMemoryEventStore(), Shipment, publisher=bus
    )
    ShipmentService(shipment_repo).record(
        order_id=order_id, lines=[{"line_id": "l_a", "quantity": "10"}], carrier="UPS"
    )
    bus.run_until_empty()

    order = order_repo.get(order_id)
    assert order.fulfillment_status is FulfillmentStatus.FULFILLED
    assert order.state.value == "CONFIRMED"  # order lifecycle itself untouched
