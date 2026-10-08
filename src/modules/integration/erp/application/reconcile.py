"""ReconcileSweeper — fallback for missed/dropped inbound webhooks.

Runs on a schedule (EventBridge Scheduler). For each known ERP order on a connection it
polls the current native status and applies any resulting canonical transition. Webhooks
are the fast path; this guarantees eventual correctness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# reuse the inbound status port shape (order_id, CanonicalStatus)
from ..domain.status_mapping import map_native_status

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.modules.integration.webhooks_inbound.application.ports import (
        OrderLocator,
        OrderStatusPort,
    )
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
        sync_shipments: Callable[[str, list[Any]], None] | None = None,
        sync_invoices: Callable[[str, list[Any]], None] | None = None,
        discover: Callable[[ConnectionId], list[str]] | None = None,
    ) -> None:
        self._connections = connections
        self._adapter_for = adapter_for
        self._locator = locator
        self._order_status = order_status
        self._sync_shipments = sync_shipments
        self._sync_invoices = sync_invoices
        self._discover = discover

    def run(self, connection_id: ConnectionId, erp_order_ids: list[str]) -> int:
        """Poll each ERP order; apply any canonical transition. Returns #transitions applied.

        `discover`, when set, adopts sales orders that already exist in the ERP and adds
        their ids to this sweep.
        """
        if self._discover is not None:
            erp_order_ids = list(dict.fromkeys([*self._discover(connection_id), *erp_order_ids]))
        target = self._connections.resolve(connection_id)
        if target is None:
            return 0
        adapter = self._adapter_for(target.erp_type)
        applied = 0
        for erp_order_id in erp_order_ids:
            native_fields = adapter.fetch_status(target, erp_order_id)
            if native_fields is None:
                continue
            order_id = self._locator.find_order(connection_id, erp_order_id)
            if order_id is None:
                continue
            status = map_native_status(target.erp_type, native_fields)
            if status is not None:
                self._order_status.apply_status(order_id, status)
                applied += 1
            if self._sync_shipments is not None:
                self._sync_shipments(str(order_id), adapter.fetch_shipments(target, erp_order_id))
            if self._sync_invoices is not None:
                self._sync_invoices(str(order_id), adapter.fetch_invoices(target, erp_order_id))
        return applied
