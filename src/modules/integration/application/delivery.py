"""DeliveryHandler — the `order-delivery` consumer.

Consumes `OrderReadyForDelivery`, resolves the target connection, reads the order
payload, submits via the ERP adapter, and drives the order aggregate:
- success  -> send_to_erp(erp_order_id)
- terminal -> reject
- transient-> mark_retrying + raise (so the queue redrives the message)
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from src.shared.eventsourcing import StoredEvent
from src.shared.types import ConnectionId, OrderId

from .ports import ConnectionResolver, ErpAdapter, OrderCommandPort, OrderReader

log = logging.getLogger(__name__)


class DeliveryRetry(Exception):
    """Raised to signal the queue to redrive the message (transient ERP failure)."""


class DeliveryHandler:
    def __init__(
        self,
        *,
        connections: ConnectionResolver,
        orders_read: OrderReader,
        orders_cmd: OrderCommandPort,
        adapter_for: Callable[[str], ErpAdapter],
    ) -> None:
        self._connections = connections
        self._orders_read = orders_read
        self._orders_cmd = orders_cmd
        self._adapter_for = adapter_for

    def handle(self, event: StoredEvent) -> None:
        if event.event_type != "OrderReadyForDelivery":
            return
        order_id = OrderId(str(event.payload["order_id"]))
        connection_id = ConnectionId(str(event.payload["owning_connection_id"]))

        target = self._connections.resolve(connection_id)
        if target is None:
            self._orders_cmd.reject(order_id, "connection_unavailable", "target ERP connection unavailable")
            return

        payload = self._orders_read.read_payload(order_id)
        if payload is None:
            self._orders_cmd.reject(order_id, "order_not_found", "order payload unavailable")
            return

        adapter = self._adapter_for(target.erp_type)
        # Declared, not gated on yet (ADR-0015) — logged so a capability gap (e.g. this
        # ERP doesn't support tax) is visible in context, rather than only inferable
        # from reading the adapter's own source.
        log.debug("submitting via %s, capabilities=%s", target.erp_type, sorted(getattr(adapter, "capabilities", frozenset())))
        result = adapter.submit(target, payload)
        if result.success:
            assert result.erp_order_id is not None
            self._orders_cmd.send_to_erp(order_id, result.erp_order_id)
        elif result.terminal:
            self._orders_cmd.reject(order_id, "erp_rejected", result.error or "ERP rejected the order")
        else:
            self._orders_cmd.mark_retrying(order_id, attempt=1, next_retry_at="")
            raise DeliveryRetry(result.error or "transient ERP failure")
