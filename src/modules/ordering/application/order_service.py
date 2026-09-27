"""OrderService — the write side (commands) for orders."""

from __future__ import annotations

from src.shared.eventsourcing import EventSourcedRepository
from src.shared.types import OrderId, TenantId, generate_id

from ..domain.aggregate import Order
from ..domain.models import OrderLine


class OrderService:
    def __init__(self, repository: EventSourcedRepository[Order]) -> None:
        self._repository = repository

    def place_order(
        self, *, tenant_id: TenantId, client_reference: str, lines: list[OrderLine]
    ) -> OrderId:
        order_id = OrderId(generate_id("ord"))
        order = Order.submit(
            order_id=order_id,
            tenant_id=tenant_id,
            client_reference=client_reference,
            lines=lines,
        )
        self._repository.save(order)
        return order_id

    def cancel_order(self, order_id: OrderId, reason: str) -> None:
        order = self._repository.get(order_id)
        order.cancel(reason)
        self._repository.save(order)
