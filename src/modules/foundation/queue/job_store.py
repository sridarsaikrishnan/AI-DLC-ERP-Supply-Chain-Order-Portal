"""JobStore and IdempotencyStore (LC-1/LC-2, P-1/P-3).

The claim query uses `FOR UPDATE SKIP LOCKED` so multiple app replicas never
process the same job (P-1, NFR-U0-REL-2).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..persistence.tables import IdempotencyRow, JobRow
from .models import Job, JobStatus


class JobStore:
    def __init__(self, session: Session):
        self.session = session

    def enqueue(self, job: Job) -> str:
        row = JobRow(
            id=job.id,
            type=job.type.value,
            payload=job.payload,
            tenant_id=job.tenant_id,
            dedupe_key=job.dedupe_key,
            status=JobStatus.PENDING.value,
            attempt_count=0,
            max_attempts=job.max_attempts,
            next_visible_at=datetime.now(timezone.utc),
            correlation_id=job.correlation_id,
        )
        self.session.add(row)
        self.session.flush()
        return job.id

    def claim_batch(self, limit: int = 10) -> list[JobRow]:
        """Claim up to `limit` due jobs using SELECT ... FOR UPDATE SKIP LOCKED."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(JobRow)
            .where(
                JobRow.status.in_([JobStatus.PENDING.value]),
                JobRow.next_visible_at <= now,
            )
            .order_by(JobRow.next_visible_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = list(self.session.execute(stmt).scalars().all())
        for row in rows:
            row.status = JobStatus.IN_PROGRESS.value
            row.attempt_count += 1
        self.session.flush()
        return rows

    def mark_succeeded(self, row: JobRow) -> None:
        row.status = JobStatus.SUCCEEDED.value
        self.session.flush()

    def reschedule_or_fail(self, row: JobRow, backoff_cap_ms: int, base_ms: int = 1000) -> None:
        """Exponential backoff with cap (P-2). Fail when attempts exhausted (BR-3.2)."""
        if row.attempt_count >= row.max_attempts:
            row.status = JobStatus.FAILED.value
        else:
            delay_ms = min(base_ms * (2 ** (row.attempt_count - 1)), backoff_cap_ms)
            row.status = JobStatus.PENDING.value
            row.next_visible_at = datetime.now(timezone.utc) + timedelta(milliseconds=delay_ms)
        self.session.flush()


class IdempotencyStore:
    """Durable idempotency via UNIQUE(dedupe_key) (P-3, BR-3.3)."""

    def __init__(self, session: Session):
        self.session = session

    def claim(self, dedupe_key: str) -> bool:
        """Return True if this is the first time we've seen the key (safe to perform side effects).
        Return False if already processed."""
        self.session.add(IdempotencyRow(dedupe_key=dedupe_key))
        try:
            self.session.flush()
            return True
        except IntegrityError:
            self.session.rollback()
            return False
