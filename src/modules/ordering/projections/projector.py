"""OrderProjector — builds order read models from the event stream (the `projections`
consumer), and feeds the reverse-routing locator when an order gets its ERP id.
"""

from __future__ import annotations

from typing import Protocol

from src.shared.eventsourcing import StoredEvent
from src.shared.types import ConnectionId, OrderId

from ..domain.models import OrderState
from .read_models import OrderLineView
from .store import OrderProjectionStore


class LocatorSink(Protocol):
    """Reverse-routing sink: remember which order an (ERP connection, erp order id) maps to."""

    def record(self, connection_id: ConnectionId, erp_order_id: str, order_id: OrderId) -> None: ...


_STATE_EVENTS: dict[str, OrderState] = {
    "OrderValidated": OrderState.VALIDATED,
    "OrderReadyForDelivery": OrderState.READY_FOR_DELIVERY,
    "OrderSentToErp": OrderState.SENT_TO_ERP,
    "OrderConfirmed": OrderState.CONFIRMED,
    "OrderFulfilled": OrderState.FULFILLED,
    "OrderClosed": OrderState.CLOSED,
    "OrderRejected": OrderState.REJECTED,
    "OrderRetrying": OrderState.RETRYING,
    "OrderCancelled": OrderState.CANCELLED,
}


class OrderProjector:
    def __init__(self, store: OrderProjectionStore, locator: LocatorSink | None = None) -> None:
        self._store = store
        self._locator = locator

    def handle(self, event: StoredEvent) -> None:
        payload = event.payload
        order_id = str(payload.get("order_id", event.stream_id))
        at = event.occurred_at.isoformat()

        if event.event_type == "OrderSubmitted":
            self._store.create(
                order_id=order_id,
                tenant_id=str(payload["tenant_id"]),
                client_reference=str(payload["client_reference"]),
                lines=[
                    OrderLineView(
                        product_key=str(line["product_key"]),
                        quantity=float(line["quantity"]),
                        unit_of_measure=str(line.get("unit_of_measure", "")),
                    )
                    for line in payload.get("lines", [])
                ],
            )
            self._store.set_state(order_id, OrderState.SUBMITTED, at)
            return

        if event.event_type == "OrderValidated":
            self._store.set_owning_connection(order_id, str(payload["owning_connection_id"]))

        if event.event_type == "OrderSentToErp":
            erp_order_id = str(payload["erp_order_id"])
            self._store.set_erp_order_id(order_id, erp_order_id)
            operator = self._store.get_operator_view(order_id)
            if self._locator is not None and operator is not None and operator.owning_connection_id:
                self._locator.record(
                    ConnectionId(operator.owning_connection_id), erp_order_id, OrderId(order_id)
                )

        state = _STATE_EVENTS.get(event.event_type)
        if state is not None:
            self._store.set_state(order_id, state, at)
