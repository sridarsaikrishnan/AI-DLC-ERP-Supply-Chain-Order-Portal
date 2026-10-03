from __future__ import annotations

from decimal import Decimal

from src.modules.catalog.application.service import CatalogService
from src.modules.catalog.infrastructure.memory import InMemoryItemRepository
from src.modules.ordering.application.order_service import OrderService
from src.modules.ordering.domain.aggregate import Order
from src.modules.ordering.domain.models import OrderLine
from src.modules.ordering.projections.projector import OrderProjector
from src.modules.ordering.projections.store import OrderProjectionStore
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.messaging import InMemoryMessageBus
from src.shared.money import Money
from src.shared.types import ConnectionId, OrderId, TenantId


def _wire() -> tuple[OrderService, EventSourcedRepository[Order], InMemoryMessageBus, OrderProjectionStore]:
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    projections = OrderProjectionStore()
    bus.subscribe("projections", OrderProjector(projections).handle)
    return OrderService(repo, InMemoryItemRepository()), repo, bus, projections


def test_reseller_view_reflects_submission_and_hides_erp_identity() -> None:
    svc, _repo, bus, projections = _wire()
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-1",
        lines=[OrderLine(product_key="ANVIL", quantity=2, unit_of_measure="EA")],
    )
    bus.run_until_empty()

    view = projections.get_reseller_view("tnt_a", order_id)
    assert view is not None
    assert view.client_reference == "PO-1"
    assert view.status == "Submitted"
    assert [l.product_key for l in view.lines] == ["ANVIL"]
    # FR-19: reseller view type has no ERP identity fields at all
    assert not hasattr(view, "owning_connection_id")
    assert not hasattr(view, "erp_order_id")


def test_order_resolves_catalog_price_and_projection_computes_subtotal() -> None:
    items = InMemoryItemRepository()
    CatalogService(items).sync_item(
        sku="ANVIL", name="Anvil", owning_connection_id=ConnectionId("conn_1"), unit_price=Money(Decimal("19.99"), "USD")
    )
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    projections = OrderProjectionStore()
    bus.subscribe("projections", OrderProjector(projections).handle)
    svc = OrderService(repo, items)

    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-1",
        lines=[OrderLine(product_key="ANVIL", quantity=2, unit_of_measure="EA")],
    )
    bus.run_until_empty()

    view = projections.get_reseller_view("tnt_a", order_id)
    assert view is not None
    assert view.lines[0].unit_price == Money(Decimal("19.99"), "USD")
    assert view.lines[0].line_total == Money(Decimal("39.98"), "USD")  # 2 * 19.99
    assert view.subtotal == Money(Decimal("39.98"), "USD")


def test_unpriced_item_leaves_subtotal_none() -> None:
    svc, _repo, bus, projections = _wire()  # empty catalog — SKU never synced
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"), client_reference="PO-1", lines=[OrderLine("ANVIL", 2, "EA")]
    )
    bus.run_until_empty()

    view = projections.get_reseller_view("tnt_a", order_id)
    assert view is not None
    assert view.lines[0].unit_price is None
    assert view.subtotal is None


def test_tenant_scoping_blocks_cross_tenant_read() -> None:
    svc, _repo, bus, projections = _wire()
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"), client_reference="PO-1", lines=[OrderLine("ANVIL", 1, "EA")]
    )
    bus.run_until_empty()
    assert projections.get_reseller_view("tnt_b", order_id) is None  # other tenant cannot see it


def test_operator_view_exposes_erp_identity_and_timeline() -> None:
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    projections = OrderProjectionStore()
    bus.subscribe("projections", OrderProjector(projections).handle)

    order = Order.submit(
        order_id=OrderId("ord_1"),
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-1",
        lines=[OrderLine("ANVIL", 1, "EA")],
    )
    order.validate(ConnectionId("conn_1"))
    order.mark_ready_for_delivery()
    order.send_to_erp("S00001")
    repo.save(order)
    bus.run_until_empty()

    operator = projections.get_operator_view("ord_1")
    assert operator is not None
    assert operator.owning_connection_id == "conn_1"
    assert operator.erp_order_id == "S00001"
    assert operator.status == "Sent to ERP"
    assert operator.timeline[-1].status == "Sent to ERP"


def test_projector_feeds_reverse_routing_locator() -> None:
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    projections = OrderProjectionStore()

    recorded: list[tuple[str, str, str]] = []

    class Locator:
        def record(self, connection_id: ConnectionId, erp_order_id: str, order_id: OrderId) -> None:
            recorded.append((str(connection_id), erp_order_id, str(order_id)))

    bus.subscribe("projections", OrderProjector(projections, locator=Locator()).handle)

    order = Order.submit(order_id=OrderId("ord_9"), tenant_id=TenantId("t"), client_reference="r", lines=[OrderLine("ANVIL", 1, "EA")])
    order.validate(ConnectionId("conn_1"))
    order.mark_ready_for_delivery()
    order.send_to_erp("S00099")
    repo.save(order)
    bus.run_until_empty()

    assert recorded == [("conn_1", "S00099", "ord_9")]
