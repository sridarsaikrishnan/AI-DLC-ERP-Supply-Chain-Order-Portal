"""Reconcile scheduler — periodically sweeps each connection for missed webhook updates."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from src.modules.integration.application.reconcile import ReconcileSweeper
from src.shared.types import ConnectionId

log = logging.getLogger(__name__)


class ReconcileScheduler:
    def __init__(
        self,
        sweeper: ReconcileSweeper,
        connections_provider: Callable[[], list[ConnectionId]],
        open_orders_provider: Callable[[ConnectionId], list[str]],
        interval_seconds: int,
    ) -> None:
        self._sweeper = sweeper
        self._connections_provider = connections_provider
        self._open_orders_provider = open_orders_provider
        self._interval = interval_seconds

    def run_forever(self) -> None:  # pragma: no cover - long-running loop
        while True:
            for connection_id in self._connections_provider():
                try:
                    self._sweeper.run(connection_id, self._open_orders_provider(connection_id))
                except Exception:  # noqa: BLE001 - one connection's failure (bad secret,
                    # unreachable ERP) must not stop the sweep for every other connection,
                    # or kill this loop until the next scheduler restart.
                    log.exception("reconcile sweep failed for connection_id=%s", connection_id)
            time.sleep(self._interval)
