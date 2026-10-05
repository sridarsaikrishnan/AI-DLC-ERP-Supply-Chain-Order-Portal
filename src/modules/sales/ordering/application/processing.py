"""OrderProcessor — consumes OrderSubmitted and validates the tenant's binding to the
connection the order was already routed to (by its quote, at issue time — Increment 7).
This is the `order-processing` consumer's logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.shared.types import ConnectionId, TenantId

if TYPE_CHECKING:
    from src.shared.eventsourcing import EventSourcedRepository, StoredEvent

    from ..domain.aggregate import Order
    from .ports import BindingQuery


class OrderProcessor:
    def __init__(self, repository: EventSourcedRepository[Order], bindings: BindingQuery) -> None:
        self._repository = repository
        self._bindings = bindings

    def handle(self, event: StoredEvent) -> None:
        if event.event_type != "OrderSubmitted":
            return
        payload = event.payload
        tenant_id = TenantId(str(payload["tenant_id"]))
        connection_id = ConnectionId(str(payload["routed_to_connection_id"]))

        order = self._repository.get(str(payload["order_id"]))

        if self._bindings.is_bound(tenant_id, connection_id):
            order.validate()
            order.accept()
        else:
            order.reject("no_binding", "no verified binding to the target connection")

        self._repository.save(order)
