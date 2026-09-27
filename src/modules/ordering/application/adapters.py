"""Adapters that let other modules drive/read the Order aggregate through narrow ports.

- `OrderCommandAdapter` implements integration's `OrderCommandPort` (delivery outcomes).
- `OrderReaderAdapter` implements integration's `OrderReader` (payload for the ERP request).
- `StatusApplier` implements webhooks_inbound's `OrderStatusPort` (inbound status -> lifecycle),
  advancing through valid intermediate transitions and ignoring stale/out-of-order updates.
"""

from __future__ import annotations

from typing import Any

from src.modules.integration.domain.status_mapping import CanonicalStatus
from src.shared.eventsourcing import EventSourcedRepository
from src.shared.types import OrderId

from ..domain.aggregate import Order
from ..domain.errors import OrderInvalidTransition
from ..projections.store import OrderProjectionStore


class OrderCommandAdapter:
    def __init__(self, repository: EventSourcedRepository[Order]) -> None:
        self._repository = repository

    def send_to_erp(self, order_id: OrderId, erp_order_id: str) -> None:
        order = self._repository.get(order_id)
        order.send_to_erp(erp_order_id)
        self._repository.save(order)

    def reject(self, order_id: OrderId, reason_code: str, message: str) -> None:
        order = self._repository.get(order_id)
        order.reject(reason_code, message)
        self._repository.save(order)

    def mark_retrying(self, order_id: OrderId, attempt: int, next_retry_at: str) -> None:
        order = self._repository.get(order_id)
        order.mark_retrying(attempt, next_retry_at)
        self._repository.save(order)


class OrderReaderAdapter:
    def __init__(self, projections: OrderProjectionStore) -> None:
        self._projections = projections

    def read_payload(self, order_id: OrderId) -> dict[str, Any] | None:
        view = self._projections.get_operator_view(order_id)
        if view is None:
            return None
        return {
            "client_reference": view.client_reference,
            "partner_name": view.client_reference,
            "lines": [
                {"product_key": line.product_key, "quantity": line.quantity, "unit_of_measure": line.unit_of_measure}
                for line in view.lines
            ],
        }


class StatusApplier:
    """Drives the order toward the canonical status implied by an ERP update."""

    def __init__(self, repository: EventSourcedRepository[Order]) -> None:
        self._repository = repository

    def apply_status(self, order_id: OrderId, status: CanonicalStatus) -> None:
        order = self._repository.get(order_id)
        if status is CanonicalStatus.CANCELLED:
            self._try(order.cancel, "cancelled in ERP")
        else:
            progression = [CanonicalStatus.CONFIRMED, CanonicalStatus.FULFILLED, CanonicalStatus.CLOSED]
            steps = [order.confirm, order.fulfill, order.close]
            for step in steps[: progression.index(status) + 1]:
                self._try(step)
        self._repository.save(order)

    @staticmethod
    def _try(fn: Any, *args: Any) -> None:
        try:
            fn(*args)
        except OrderInvalidTransition:
            pass  # stale / out-of-order ERP update — lifecycle is monotonic
