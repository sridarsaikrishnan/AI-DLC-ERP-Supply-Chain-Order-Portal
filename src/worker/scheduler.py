"""Reconcile scheduler — periodically sweeps each connection for missed webhook updates."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.modules.integration.erp.application.reconcile import ReconcileSweeper
    from src.shared.types import ConnectionId

    from .connection_lock import ConnectionLock

log = logging.getLogger(__name__)


class ReconcileScheduler:
    def __init__(
        self,
        sweeper: ReconcileSweeper,
        connections_provider: Callable[[], list[ConnectionId]],
        open_orders_provider: Callable[[ConnectionId], list[str]],
        interval_seconds: int,
        lock: ConnectionLock | None = None,
    ) -> None:
        self._sweeper = sweeper
        self._connections_provider = connections_provider
        self._open_orders_provider = open_orders_provider
        self._interval = interval_seconds
        # None (default) = no locking — fine for a single replica (tests, local dev).
        # A real `PostgresConnectionLock` is what makes running >1 `worker` replica safe.
        self._lock = lock

    def run_forever(self) -> None:  # pragma: no cover - long-running loop
        while True:
            self.run_once()
            time.sleep(self._interval)

    def run_once(self) -> None:
        for connection_id in self._connections_provider():
            try:
                self._sweep_one(connection_id)
            except Exception:
                # unreachable ERP) must not stop the sweep for every other connection,
                # or kill this loop until the next scheduler restart.
                log.exception("reconcile sweep failed for connection_id=%s", connection_id)

    def _sweep_one(self, connection_id: ConnectionId) -> None:
        if self._lock is None:
            self._sweeper.run(connection_id, self._open_orders_provider(connection_id))
            return
        with self._lock.try_acquire(str(connection_id)) as acquired:
            if not acquired:
                log.info(
                    "skip connection_id=%s — already being swept by another worker replica",
                    connection_id,
                )
                return
            self._sweeper.run(connection_id, self._open_orders_provider(connection_id))
