from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.sales.ordering.domain.aggregate import Order
from src.modules.sales.ordering.domain.models import FulfillmentStatus, OrderLine
from src.modules.sales.shipment.application.service import ShipmentService
from src.modules.sales.shipment.domain.aggregate import Shipment
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
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


# --- coordinating service: the Shipment -> Order link -------------------------------


def test_shipment_service_updates_order_derived_status() -> None:
    event_store = InMemoryEventStore()
    order_repo, order_id = _confirmed_order(event_store)
    shipment_repo: EventSourcedRepository[Shipment] = EventSourcedRepository(
        InMemoryEventStore(), Shipment
    )
    service = ShipmentService(shipment_repo, order_repo)

    service.record(order_id=order_id, lines=[{"line_id": "l_a", "quantity": "10"}], carrier="UPS")

    order = order_repo.get(order_id)
    assert order.fulfillment_status is FulfillmentStatus.FULFILLED
    assert order.state.value == "CONFIRMED"  # order lifecycle itself untouched
