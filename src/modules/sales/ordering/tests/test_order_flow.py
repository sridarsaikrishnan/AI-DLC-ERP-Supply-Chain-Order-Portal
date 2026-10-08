"""Adopting a sales order that already exists in the ERP."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from src.modules.sales.ordering.application.order_service import OrderService
from src.modules.sales.ordering.domain.aggregate import Order
from src.modules.sales.ordering.domain.models import OrderState
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.types import ConnectionId, TenantId


def test_observe_erp_order_links_it_without_creating_one() -> None:
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order)
    service = OrderService(repo)
    line = SimpleNamespace(product_key="DEMO-BOX", quantity="2", unit_price="100", currency="USD")

    order_id = service.observe_erp_order(
        tenant_id=TenantId("tnt_a"),
        connection_id="conn_1",
        erp_order_id="S00042",
        client_reference="PO-9",
        lines=[line],
    )
    again = service.observe_erp_order(
        tenant_id=TenantId("tnt_a"),
        connection_id="conn_1",
        erp_order_id="S00042",
        client_reference="PO-9",
        lines=[line],
    )

    assert order_id == again
    order = repo.get(order_id)
    assert order.state is OrderState.SENT_TO_ERP
    assert order.erp_order_id == "S00042"
    assert order.owning_connection_id == ConnectionId("conn_1")
    assert order.lines[0].product_key == "DEMO-BOX"
    assert order.lines[0].quantity == Decimal("2")
    assert [record.event_type for record in store.load(str(order_id))] == ["OrderObserved"]
