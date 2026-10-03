"""ReconcileSweeper — fallback for missed/dropped inbound webhooks.

Runs on a schedule (EventBridge Scheduler). For each known ERP order on a connection it
polls the current native status and applies any resulting canonical transition. Webhooks
are the fast path; this guarantees eventual correctness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# reuse the inbound status port shape (order_id, CanonicalStatus)
from ..domain.status_mapping import map_native_status

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.modules.webhooks_inbound.application.ports import OrderLocator, OrderStatusPort
    from src.shared.types import ConnectionId

    from .ports import ConnectionResolver, ErpAdapter


class ReconcileSweeper:
    def __init__(
        self,
        *,
        connections: ConnectionResolver,
        adapter_for: Callable[[str], ErpAdapter],
        locator: OrderLocator,
        order_status: OrderStatusPort,
    ) -> None:
        self._connections = connections
        self._adapter_for = adapter_for
        self._locator = locator
        self._order_status = order_status

    def run(self, connection_id: ConnectionId, erp_order_ids: list[str]) -> int:
        """Poll each ERP order; apply any canonical transition. Returns #transitions applied."""
        target = self._connections.resolve(connection_id)
        if target is None:
            return 0
        adapter = self._adapter_for(target.erp_type)
        applied = 0
        for erp_order_id in erp_order_ids:
            native_fields = adapter.fetch_status(target, erp_order_id)
            if native_fields is None:
                continue
            status = map_native_status(target.erp_type, native_fields)
            if status is None:
                continue
            order_id = self._locator.find_order(connection_id, erp_order_id)
            if order_id is None:
                continue
            self._order_status.apply_status(order_id, status)
            applied += 1
        return applied
