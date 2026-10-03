"""End-to-end write path: place_order -> OrderSubmitted on the bus -> OrderProcessor
routes -> order becomes READY_FOR_DELIVERY (or REJECTED). Uses the in-memory store + bus.
"""

from __future__ import annotations

from src.modules.catalog.infrastructure.memory import InMemoryItemRepository
from src.modules.ordering.application.order_service import OrderService
from src.modules.ordering.application.processing import OrderProcessor
from src.modules.ordering.domain.aggregate import Order
from src.modules.ordering.domain.models import OrderLine, OrderState
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.messaging import InMemoryMessageBus
from src.shared.types import ConnectionId, TenantId


class FakeOwnership:
    def __init__(self, owners: dict[str, str]) -> None:
        self._owners = owners

    def owner_of(self, product_key: str) -> ConnectionId | None:
        value = self._owners.get(product_key)
        return ConnectionId(value) if value else None


class FakeBindings:
    def __init__(self, bound: set[tuple[str, str]]) -> None:
        self._bound = bound

    def is_bound(self, tenant_id: TenantId, connection_id: ConnectionId) -> bool:
        return (str(tenant_id), str(connection_id)) in self._bound


def _wire(owners: dict[str, str], bound: set[tuple[str, str]]):
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    processor = OrderProcessor(repo, FakeOwnership(owners), FakeBindings(bound))
    bus.subscribe("order-processing", processor.handle, event_types={"OrderSubmitted"})
    return OrderService(repo, InMemoryItemRepository()), repo, bus


def test_place_order_routes_to_owning_connection() -> None:
    svc, repo, bus = _wire({"ANVIL": "conn_1"}, {("tnt_a", "conn_1")})
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-1",
        lines=[OrderLine(product_key="ANVIL", quantity=1, unit_of_measure="EA")],
    )
    bus.run_until_empty()

    order = repo.get(order_id)
    assert order.state is OrderState.READY_FOR_DELIVERY
    assert order.owning_connection_id == ConnectionId("conn_1")


def test_place_order_mixed_erp_is_rejected() -> None:
    svc, repo, bus = _wire(
        {"ANVIL": "conn_1", "ROCKET": "conn_2"},
        {("tnt_a", "conn_1"), ("tnt_a", "conn_2")},
    )
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-2",
        lines=[
            OrderLine(product_key="ANVIL", quantity=1, unit_of_measure="EA"),
            OrderLine(product_key="ROCKET", quantity=1, unit_of_measure="EA"),
        ],
    )
    bus.run_until_empty()

    order = repo.get(order_id)
    assert order.state is OrderState.REJECTED


def test_place_order_without_binding_is_rejected() -> None:
    svc, repo, bus = _wire({"ANVIL": "conn_1"}, set())  # no verified binding
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-3",
        lines=[OrderLine(product_key="ANVIL", quantity=1, unit_of_measure="EA")],
    )
    bus.run_until_empty()
    assert repo.get(order_id).state is OrderState.REJECTED
