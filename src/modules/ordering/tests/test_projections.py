from __future__ import annotations

from src.modules.ordering.application.order_service import OrderService
from src.modules.ordering.domain.aggregate import Order
from src.modules.ordering.domain.models import OrderLine
from src.modules.ordering.projections.projector import OrderProjector
from src.modules.ordering.projections.store import OrderProjectionStore
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.messaging import InMemoryMessageBus
from src.shared.types import ConnectionId, OrderId, TenantId


def _wire() -> tuple[OrderService, EventSourcedRepository[Order], InMemoryMessageBus, OrderProjectionStore]:
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    projections = OrderProjectionStore()
    bus.subscribe("projections", OrderProjector(projections).handle)
    return OrderService(repo), repo, bus, projections


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
