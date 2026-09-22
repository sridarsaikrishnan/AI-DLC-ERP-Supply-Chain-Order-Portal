"""Background poller (LC-2, P-1).

Short-interval loop that drives the WorkerHost. Runs inside each app replica when
APP_ROLE includes worker (default: both). Job-level SKIP LOCKED keeps replicas safe.
"""

from __future__ import annotations

import os
import threading
import time

from ....shared.logging import get_logger
from .worker import WorkerHost

logger = get_logger("foundation.queue.poller")


class Poller:
    def __init__(self, worker: WorkerHost):
        self.worker = worker
        self.interval_s = int(os.environ.get("POLL_INTERVAL_MS", "1500")) / 1000.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="job-poller", daemon=True)
        self._thread.start()
        logger.info("poller started", extra={"extra_fields": {"interval_s": self.interval_s}})

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.worker.process_batch()
            except Exception:  # noqa: BLE001
                logger.exception("poller iteration error")
            self._stop.wait(self.interval_s)
