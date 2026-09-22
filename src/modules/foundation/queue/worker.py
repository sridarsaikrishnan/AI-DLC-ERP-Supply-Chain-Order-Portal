"""HandlerRegistry and WorkerHost (LC-2, Process 4).

Workers reconstruct a SecurityContext from the job's tenant id (BR-3.4), invoke
the registered handler (idempotent by dedupe_key), and apply retry/backoff (P-2).
"""

from __future__ import annotations

import os
from typing import Callable

from sqlalchemy.orm import Session

from ..context.security_context import context_from_tenant, use_context
from ....shared.correlation import set_correlation_id
from ....shared.logging import get_logger
from ....shared import metrics
from ..persistence.tables import JobRow
from .job_store import IdempotencyStore, JobStore
from .models import JobType

logger = get_logger("foundation.queue.worker")

# handler signature: (session, payload: dict) -> None
Handler = Callable[[Session, dict], None]


class HandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[JobType, Handler] = {}

    def register(self, job_type: JobType, handler: Handler) -> None:
        self._handlers[job_type] = handler

    def get(self, job_type: JobType) -> Handler | None:
        return self._handlers.get(job_type)


class WorkerHost:
    def __init__(self, session_factory, registry: HandlerRegistry):
        self.session_factory = session_factory
        self.registry = registry
        self.backoff_cap_ms = int(os.environ.get("RETRY_BACKOFF_CAP_MS", "60000"))

    def process_batch(self, limit: int = 10) -> int:
        """Claim and process a batch. Returns number of jobs processed."""
        session: Session = self.session_factory()
        processed = 0
        try:
            store = JobStore(session)
            idem = IdempotencyStore(session)
            rows = store.claim_batch(limit=limit)
            for row in rows:
                self._process_one(session, store, idem, row)
                processed += 1
            session.commit()
        except Exception:  # noqa: BLE001 - worker loop must not crash on one bad job
            session.rollback()
            logger.exception("worker batch failed")
        finally:
            session.close()
        return processed

    def _process_one(self, session: Session, store: JobStore, idem: IdempotencyStore, row: JobRow) -> None:
        set_correlation_id(row.correlation_id)
        job_type = JobType(row.type)
        handler = self.registry.get(job_type)
        if handler is None:
            logger.error("no handler for job type", extra={"extra_fields": {"job_type": row.type}})
            store.reschedule_or_fail(row, self.backoff_cap_ms)
            return

        # Idempotency guard (BR-3.3): only perform side effects once per dedupe_key
        if not idem.claim(row.dedupe_key):
            logger.info("duplicate job skipped", extra={"extra_fields": {"dedupe_key": row.dedupe_key}})
            store.mark_succeeded(row)
            metrics.increment("jobs_duplicate_skipped")
            return

        try:
            with use_context(context_from_tenant(row.tenant_id)):
                handler(session, row.payload)
            store.mark_succeeded(row)
            metrics.increment("jobs_succeeded")
        except Exception:  # noqa: BLE001
            logger.exception("job handler failed", extra={"extra_fields": {"job_id": row.id}})
            store.reschedule_or_fail(row, self.backoff_cap_ms)
            metrics.increment("jobs_failed")
