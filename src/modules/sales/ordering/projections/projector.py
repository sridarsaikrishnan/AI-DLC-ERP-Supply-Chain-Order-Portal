"""OrderProjector — builds order read models from the event stream (the `projections`
consumer), and feeds the reverse-routing locator when an order gets its ERP id.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Protocol

from src.shared.types import ConnectionId, OrderId

from ..domain.calculations import line_total
from ..domain.models import OrderLine, OrderState
from .read_models import OrderLineView, Parties

if TYPE_CHECKING:
    from src.shared.eventsourcing import StoredEvent

    from .store import OrderProjectionStore


class LocatorSink(Protocol):
    """Reverse-routing sink: remember which order an (ERP connection, erp order id) maps to."""

    def record(self, connection_id: ConnectionId, erp_order_id: str, order_id: OrderId) -> None: ...


_STATE_EVENTS: dict[str, OrderState] = {
    "OrderValidated": OrderState.VALIDATED,
    "OrderReadyForDelivery": OrderState.ACCEPTED,  # renamed state, same persisted event (Q2=A)
    "OrderSentToErp": OrderState.SENT_TO_ERP,
    "OrderConfirmed": OrderState.CONFIRMED,
    "OrderClosed": OrderState.CLOSED,
    "OrderRejected": OrderState.REJECTED,
    "OrderRetrying": OrderState.RETRYING,
    "OrderCancelled": OrderState.CANCELLED,
    # "OrderFulfilled" intentionally absent — FULFILLED left the lifecycle (FR-A6).
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
                lines=[self._line_view(line) for line in payload.get("lines", [])],
                parties=Parties(
                    end_customer_name=str(payload.get("end_customer_name", "")),
                    ship_to=str(payload.get("ship_to", "")),
                    subsidiary_id=str(payload.get("subsidiary_id", "")),
                    quote_id=str(payload.get("quote_id", "")),
                ),
            )
            self._store.set_owning_connection(
                order_id, str(payload.get("routed_to_connection_id", ""))
            )
            self._store.set_state(order_id, OrderState.SUBMITTED, at)
            return

        if event.event_type == "OrderObserved":
            self._store.create(
                order_id=order_id,
                tenant_id=str(payload["tenant_id"]),
                client_reference=str(payload["client_reference"]),
                lines=[self._line_view(line) for line in payload.get("lines", [])],
                parties=Parties(
                    end_customer_name="",
                    ship_to="",
                    subsidiary_id="",
                    quote_id="",
                ),
            )
            connection_id = str(payload.get("routed_to_connection_id", ""))
            self._store.set_owning_connection(order_id, connection_id)
            erp_order_id = str(payload["erp_order_id"])
            self._store.set_erp_order_id(order_id, erp_order_id)
            self._store.set_state(order_id, OrderState.SENT_TO_ERP, at)
            if self._locator is not None and connection_id:
                self._locator.record(ConnectionId(connection_id), erp_order_id, OrderId(order_id))
            return

        if event.event_type == "OrderSentToErp":
            erp_order_id = str(payload["erp_order_id"])
            self._store.set_erp_order_id(order_id, erp_order_id)
            operator = self._store.get_operator_view(order_id)
            if self._locator is not None and operator is not None and operator.owning_connection_id:
                self._locator.record(
                    ConnectionId(operator.owning_connection_id), erp_order_id, OrderId(order_id)
                )

        if event.event_type == "OrderLineFulfilled":
            key = str(payload.get("line_id") or payload.get("product_key") or "")
            self._store.record_fulfillment(
                order_id,
                key,
                float(Decimal(str(payload["quantity"]))),
                payload.get("carrier"),
                payload.get("proof_of_delivery"),
            )
            return

        if event.event_type == "OrderLineInvoiced":
            key = str(payload.get("line_id") or payload.get("product_key") or "")
            self._store.record_invoice(order_id, key, float(Decimal(str(payload["quantity"]))))
            return

        if event.event_type == "OrderLineVendorDateSet":
            self._store.set_scheduled_date(
                order_id, str(payload["line_id"]), str(payload["vendor_date"])
            )
            return

        state = _STATE_EVENTS.get(event.event_type)
        if state is not None:
            self._store.set_state(order_id, state, at)

    @staticmethod
    def _line_view(line: dict) -> OrderLineView:
        order_line = OrderLine.from_dict(line)
        return OrderLineView(
            product_key=order_line.product_key,
            quantity=float(order_line.quantity),
            unit_of_measure=order_line.unit_of_measure,
            line_id=order_line.line_id,
            kind=order_line.kind,
            unit_price=order_line.unit_price,
            line_total=line_total(order_line),
            tax_rates=order_line.tax_rates,
            line_discount=order_line.line_discount,
        )
