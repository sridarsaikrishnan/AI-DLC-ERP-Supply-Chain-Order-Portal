from __future__ import annotations

from src.modules.sales.ordering.application.adapters import StatusApplier
from src.modules.sales.ordering.domain.aggregate import Order
from src.modules.sales.ordering.domain.models import OrderLine, OrderState
from src.shared.canonical_status import CanonicalStatus
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.types import OrderId, TenantId


def _sent_order(repo: EventSourcedRepository[Order]) -> OrderId:
    order = Order.submit(
        order_id=OrderId("ord_1"),
        tenant_id=TenantId("t"),
        client_reference="r",
        lines=[OrderLine(product_key="ANVIL", quantity=1, unit_of_measure="EA", line_id="l_a")],
        routed_to_connection_id="conn_1",
    )
    order.validate()
    order.accept()
    order.send_to_erp("S1")
    repo.save(order)
    return OrderId("ord_1")


def test_confirmed_then_closed() -> None:
    repo: EventSourcedRepository[Order] = EventSourcedRepository(InMemoryEventStore(), Order)
    order_id = _sent_order(repo)
    applier = StatusApplier(repo)

    applier.apply_status(order_id, CanonicalStatus.CONFIRMED)
    assert repo.get(order_id).state is OrderState.CONFIRMED

    applier.apply_status(order_id, CanonicalStatus.CLOSED)
    assert repo.get(order_id).state is OrderState.CLOSED


def test_closed_from_sent_advances_through_confirmed() -> None:
    repo: EventSourcedRepository[Order] = EventSourcedRepository(InMemoryEventStore(), Order)
    order_id = _sent_order(repo)
    StatusApplier(repo).apply_status(order_id, CanonicalStatus.CLOSED)
    assert repo.get(order_id).state is OrderState.CLOSED


def test_stale_update_is_ignored() -> None:
    repo: EventSourcedRepository[Order] = EventSourcedRepository(InMemoryEventStore(), Order)
    order_id = _sent_order(repo)
    applier = StatusApplier(repo)
    applier.apply_status(order_id, CanonicalStatus.CLOSED)
    # a late "confirmed" webhook must not move the order backwards (CLOSED is terminal)
    applier.apply_status(order_id, CanonicalStatus.CONFIRMED)
    assert repo.get(order_id).state is OrderState.CLOSED


def test_cancel_from_erp() -> None:
    repo: EventSourcedRepository[Order] = EventSourcedRepository(InMemoryEventStore(), Order)
    order_id = _sent_order(repo)
    StatusApplier(repo).apply_status(order_id, CanonicalStatus.CANCELLED)
    assert repo.get(order_id).state is OrderState.CANCELLED
