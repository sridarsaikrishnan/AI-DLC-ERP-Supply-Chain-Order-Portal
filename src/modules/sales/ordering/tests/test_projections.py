from __future__ import annotations

from decimal import Decimal

from src.modules.sales.ordering.domain.aggregate import Order
from src.modules.sales.ordering.domain.models import OrderLine
from src.modules.sales.ordering.projections.projector import OrderProjector
from src.modules.sales.ordering.projections.store import OrderProjectionStore
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.messaging import InMemoryMessageBus
from src.shared.money import Money
from src.shared.types import ConnectionId, OrderId, TenantId


def _line(
    product_key: str, qty, line_id: str, *, price: str | None = None, kind: str = "PHYSICAL"
) -> OrderLine:
    return OrderLine(
        product_key=product_key,
        quantity=qty,
        unit_of_measure="EA",
        line_id=line_id,
        kind=kind,
        unit_price=Money(Decimal(price), "USD") if price is not None else None,
    )


def _wire():
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    projections = OrderProjectionStore()
    bus.subscribe("projections", OrderProjector(projections).handle)
    return repo, bus, projections


def _observe(repo, bus, projections, **line_kwargs):
    order = Order.observe(
        order_id=OrderId("ord_1"),
        tenant_id=TenantId("tnt_a"),
        client_reference="S00001",
        lines=[_line("ANVIL", 2, "l_a", **line_kwargs)],
        connection_id="conn_1",
        erp_order_id="S00001",
    )
    repo.save(order)
    bus.run_until_empty()
    return projections


def test_reseller_view_hides_erp_identity() -> None:
    repo, bus, projections = _wire()
    _observe(repo, bus, projections)

    view = projections.get_reseller_view("tnt_a", "ord_1")
    assert view is not None
    assert view.client_reference == "S00001"
    assert view.status == "SENT_TO_ERP"
    assert [line.product_key for line in view.lines] == ["ANVIL"]
    assert not hasattr(view, "owning_connection_id")
    assert not hasattr(view, "erp_order_id")


def test_observed_line_price_projects_subtotal() -> None:
    repo, bus, projections = _wire()
    _observe(repo, bus, projections, price="19.99")

    view = projections.get_reseller_view("tnt_a", "ord_1")
    assert view is not None
    assert view.lines[0].unit_price == Money(Decimal("19.99"), "USD")
    assert view.lines[0].line_total == Money(Decimal("39.98"), "USD")
    assert view.subtotal == Money(Decimal("39.98"), "USD")


def test_line_kind_projects() -> None:
    repo, bus, projections = _wire()
    order = Order.observe(
        order_id=OrderId("ord_1"),
        tenant_id=TenantId("tnt_a"),
        client_reference="S00001",
        lines=[_line("LIC", 1, "l_a", price="5.00", kind="LICENSE")],
        connection_id="conn_1",
        erp_order_id="S00001",
    )
    repo.save(order)
    bus.run_until_empty()
    view = projections.get_reseller_view("tnt_a", "ord_1")
    assert view is not None
    assert view.lines[0].kind == "LICENSE"


def test_tenant_scoping_blocks_cross_tenant_read() -> None:
    repo, bus, projections = _wire()
    _observe(repo, bus, projections)
    assert projections.get_reseller_view("tnt_b", "ord_1") is None


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
        lines=[_line("ANVIL", 1, "l_a")],
        routed_to_connection_id="conn_1",
    )
    order.validate()
    order.accept()
    order.send_to_erp("S00001")
    repo.save(order)
    bus.run_until_empty()

    operator = projections.get_operator_view("ord_1")
    assert operator is not None
    assert operator.owning_connection_id == "conn_1"
    assert operator.erp_order_id == "S00001"
    assert operator.status == "SENT_TO_ERP"
    assert operator.timeline[-1].status == "SENT_TO_ERP"


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

    order = Order.submit(
        order_id=OrderId("ord_9"),
        tenant_id=TenantId("t"),
        client_reference="r",
        lines=[_line("ANVIL", 1, "l_a")],
        routed_to_connection_id="conn_1",
    )
    order.validate()
    order.accept()
    order.send_to_erp("S00099")
    repo.save(order)
    bus.run_until_empty()

    assert recorded == [("conn_1", "S00099", "ord_9")]
