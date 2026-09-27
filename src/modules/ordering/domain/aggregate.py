"""The Order aggregate — event-sourced via the shared kernel.

Behavior + invariants live here. State changes ONLY by applying events; every public
method guards the current lifecycle state and `emit`s a fact. Terminal transitions and
already-in-target-state calls are handled so at-least-once redelivery is safe.
"""

from __future__ import annotations

from typing import Any

from src.shared.eventsourcing import Aggregate
from src.shared.types import ConnectionId, OrderId, TenantId

from .errors import OrderInvalidTransition
from .events import (
    OrderCancelled,
    OrderConfirmed,
    OrderFulfilled,
    OrderClosed,
    OrderReadyForDelivery,
    OrderRejected,
    OrderRetrying,
    OrderSentToErp,
    OrderSubmitted,
    OrderValidated,
)
from .models import OrderLine, OrderState, TERMINAL_STATES


class Order(Aggregate):
    aggregate_type = "Order"

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.tenant_id: TenantId = TenantId("")
        self.client_reference: str = ""
        self.lines: list[OrderLine] = []
        self.product_keys: list[str] = []
        self.state: OrderState | None = None
        self.owning_connection_id: ConnectionId | None = None
        self.erp_order_id: str | None = None
        self.retry_attempt: int = 0

    # --- commands (behavior) ---
    @classmethod
    def submit(
        cls,
        *,
        order_id: OrderId,
        tenant_id: TenantId,
        client_reference: str,
        lines: list[OrderLine],
    ) -> "Order":
        if not lines:
            raise ValueError("order must have at least one line")
        for line in lines:
            if not line.product_key:
                raise ValueError("line requires a product_key")
            if line.quantity <= 0:
                raise ValueError("line quantity must be positive")

        order = cls(order_id)
        order.emit(
            OrderSubmitted(
                order_id=order_id,
                tenant_id=tenant_id,
                client_reference=client_reference,
                lines=[
                    {
                        "product_key": line.product_key,
                        "quantity": line.quantity,
                        "unit_of_measure": line.unit_of_measure,
                    }
                    for line in lines
                ],
                product_keys=[line.product_key for line in lines],
            )
        )
        return order

    def validate(self, owning_connection_id: ConnectionId) -> None:
        self._require(OrderState.SUBMITTED, "validate")
        self.emit(OrderValidated(order_id=self.id, owning_connection_id=str(owning_connection_id)))

    def mark_ready_for_delivery(self) -> None:
        self._require(OrderState.VALIDATED, "mark_ready_for_delivery")
        assert self.owning_connection_id is not None
        self.emit(
            OrderReadyForDelivery(order_id=self.id, owning_connection_id=str(self.owning_connection_id))
        )

    def reject(self, reason_code: str, reseller_message: str) -> None:
        if self.state not in (OrderState.SUBMITTED, OrderState.VALIDATED):
            raise OrderInvalidTransition(f"cannot reject in state {self.state}")
        self.emit(
            OrderRejected(order_id=self.id, reason_code=reason_code, reseller_message=reseller_message)
        )

    def send_to_erp(self, erp_order_id: str) -> None:
        if self.state not in (OrderState.READY_FOR_DELIVERY, OrderState.RETRYING):
            raise OrderInvalidTransition(f"cannot send_to_erp in state {self.state}")
        self.emit(OrderSentToErp(order_id=self.id, erp_order_id=erp_order_id))

    def mark_retrying(self, attempt: int, next_retry_at: str) -> None:
        if self.state not in (
            OrderState.READY_FOR_DELIVERY,
            OrderState.RETRYING,
            OrderState.SENT_TO_ERP,
        ):
            raise OrderInvalidTransition(f"cannot mark_retrying in state {self.state}")
        self.emit(OrderRetrying(order_id=self.id, attempt=attempt, next_retry_at=next_retry_at))

    def confirm(self) -> None:
        if self.state is OrderState.CONFIRMED:
            return  # idempotent
        self._require(OrderState.SENT_TO_ERP, "confirm")
        self.emit(OrderConfirmed(order_id=self.id))

    def fulfill(self) -> None:
        if self.state is OrderState.FULFILLED:
            return
        self._require(OrderState.CONFIRMED, "fulfill")
        self.emit(OrderFulfilled(order_id=self.id))

    def close(self) -> None:
        if self.state is OrderState.CLOSED:
            return
        self._require(OrderState.FULFILLED, "close")
        self.emit(OrderClosed(order_id=self.id))

    def cancel(self, reason: str) -> None:
        if self.state in TERMINAL_STATES or self.state is OrderState.FULFILLED:
            raise OrderInvalidTransition(f"cannot cancel in state {self.state}")
        self.emit(OrderCancelled(order_id=self.id, reason=reason))

    def _require(self, expected: OrderState, action: str) -> None:
        if self.state is not expected:
            raise OrderInvalidTransition(
                f"cannot {action} in state {self.state} (requires {expected})"
            )

    # --- state transitions (pure applies) ---
    def _apply_OrderSubmitted(self, e: OrderSubmitted) -> None:
        self.tenant_id = TenantId(e.tenant_id)
        self.client_reference = e.client_reference
        self.lines = [OrderLine(**line) for line in e.lines]
        self.product_keys = list(e.product_keys)
        self.state = OrderState.SUBMITTED

    def _apply_OrderValidated(self, e: OrderValidated) -> None:
        self.owning_connection_id = ConnectionId(e.owning_connection_id)
        self.state = OrderState.VALIDATED

    def _apply_OrderReadyForDelivery(self, e: OrderReadyForDelivery) -> None:
        self.state = OrderState.READY_FOR_DELIVERY

    def _apply_OrderRejected(self, e: OrderRejected) -> None:
        self.state = OrderState.REJECTED

    def _apply_OrderSentToErp(self, e: OrderSentToErp) -> None:
        self.erp_order_id = e.erp_order_id
        self.state = OrderState.SENT_TO_ERP

    def _apply_OrderRetrying(self, e: OrderRetrying) -> None:
        self.retry_attempt = e.attempt
        self.state = OrderState.RETRYING

    def _apply_OrderConfirmed(self, e: OrderConfirmed) -> None:
        self.state = OrderState.CONFIRMED

    def _apply_OrderFulfilled(self, e: OrderFulfilled) -> None:
        self.state = OrderState.FULFILLED

    def _apply_OrderClosed(self, e: OrderClosed) -> None:
        self.state = OrderState.CLOSED

    def _apply_OrderCancelled(self, e: OrderCancelled) -> None:
        self.state = OrderState.CANCELLED

    # --- snapshot support ---
    def snapshot_state(self) -> dict[str, Any]:
        return {
            "tenant_id": str(self.tenant_id),
            "client_reference": self.client_reference,
            "lines": [
                {"product_key": l.product_key, "quantity": l.quantity, "unit_of_measure": l.unit_of_measure}
                for l in self.lines
            ],
            "product_keys": list(self.product_keys),
            "state": self.state.value if self.state else None,
            "owning_connection_id": str(self.owning_connection_id) if self.owning_connection_id else None,
            "erp_order_id": self.erp_order_id,
            "retry_attempt": self.retry_attempt,
        }

    def restore(self, state: dict[str, Any]) -> None:
        self.tenant_id = TenantId(state["tenant_id"])
        self.client_reference = state["client_reference"]
        self.lines = [OrderLine(**line) for line in state["lines"]]
        self.product_keys = list(state["product_keys"])
        self.state = OrderState(state["state"]) if state["state"] else None
        self.owning_connection_id = (
            ConnectionId(state["owning_connection_id"]) if state["owning_connection_id"] else None
        )
        self.erp_order_id = state["erp_order_id"]
        self.retry_attempt = state["retry_attempt"]
