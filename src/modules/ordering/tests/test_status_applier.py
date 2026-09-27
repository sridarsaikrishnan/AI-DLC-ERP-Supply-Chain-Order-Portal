from __future__ import annotations

from src.modules.integration.domain.status_mapping import CanonicalStatus
from src.modules.ordering.application.adapters import StatusApplier
from src.modules.ordering.domain.aggregate import Order
from src.modules.ordering.domain.models import OrderLine, OrderState
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.types import ConnectionId, OrderId, TenantId


def _sent_order(repo: EventSourcedRepository[Order]) -> OrderId:
    order = Order.submit(
        order_id=OrderId("ord_1"), tenant_id=TenantId("t"), client_reference="r",
        lines=[OrderLine("ANVIL", 1, "EA")],
    )
    order.validate(ConnectionId("conn_1"))
    order.mark_ready_for_delivery()
    order.send_to_erp("S1")
    repo.save(order)
    return OrderId("ord_1")


def test_confirmed_then_fulfilled() -> None:
    repo: EventSourcedRepository[Order] = EventSourcedRepository(InMemoryEventStore(), Order)
    order_id = _sent_order(repo)
    applier = StatusApplier(repo)

    applier.apply_status(order_id, CanonicalStatus.CONFIRMED)
    assert repo.get(order_id).state is OrderState.CONFIRMED

    applier.apply_status(order_id, CanonicalStatus.FULFILLED)
    assert repo.get(order_id).state is OrderState.FULFILLED


def test_fulfilled_from_sent_advances_through_confirmed() -> None:
    repo: EventSourcedRepository[Order] = EventSourcedRepository(InMemoryEventStore(), Order)
    order_id = _sent_order(repo)
    StatusApplier(repo).apply_status(order_id, CanonicalStatus.FULFILLED)
    assert repo.get(order_id).state is OrderState.FULFILLED


def test_stale_update_is_ignored() -> None:
    repo: EventSourcedRepository[Order] = EventSourcedRepository(InMemoryEventStore(), Order)
    order_id = _sent_order(repo)
    applier = StatusApplier(repo)
    applier.apply_status(order_id, CanonicalStatus.FULFILLED)
    # a late "confirmed" webhook must not move the order backwards
    applier.apply_status(order_id, CanonicalStatus.CONFIRMED)
    assert repo.get(order_id).state is OrderState.FULFILLED


def test_cancel_from_erp() -> None:
    repo: EventSourcedRepository[Order] = EventSourcedRepository(InMemoryEventStore(), Order)
    order_id = _sent_order(repo)
    StatusApplier(repo).apply_status(order_id, CanonicalStatus.CANCELLED)
    assert repo.get(order_id).state is OrderState.CANCELLED
