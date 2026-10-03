"""OrderProcessor — consumes OrderSubmitted, applies ownership routing, then
validates + marks ready, or rejects. This is the `order-processing` consumer's logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.shared.types import ConnectionId, TenantId

from ..domain.routing import resolve_owning_connection

if TYPE_CHECKING:
    from src.shared.eventsourcing import EventSourcedRepository, StoredEvent

    from ..domain.aggregate import Order
    from .ports import BindingQuery, OwnershipQuery


class OrderProcessor:
    def __init__(
        self,
        repository: EventSourcedRepository[Order],
        ownership: OwnershipQuery,
        bindings: BindingQuery,
    ) -> None:
        self._repository = repository
        self._ownership = ownership
        self._bindings = bindings

    def handle(self, event: StoredEvent) -> None:
        if event.event_type != "OrderSubmitted":
            return
        payload = event.payload
        tenant_id = TenantId(str(payload["tenant_id"]))
        product_keys = list(payload["product_keys"])

        order = self._repository.get(str(payload["order_id"]))

        decision = resolve_owning_connection(
            product_keys,
            owner_of=self._ownership.owner_of,
            is_bound=lambda connection_id: self._bindings.is_bound(tenant_id, connection_id),
        )

        if decision.routed:
            assert decision.connection_id is not None
            order.validate(ConnectionId(decision.connection_id))
            order.accept()
        else:
            assert decision.reason is not None
            order.reject(decision.reason.value, decision.message or "order rejected")

        self._repository.save(order)
