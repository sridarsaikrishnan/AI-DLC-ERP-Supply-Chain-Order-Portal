"""OutboxRelay — publishes unpublished outbox rows to the bus, then marks them published.

Uses SELECT ... FOR UPDATE SKIP LOCKED so multiple relay workers don't double-publish.
Delivery is at-least-once (a crash after publish, before mark, re-publishes) — consumers
dedupe on event_id, so this is safe.
"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker, Session

from src.shared.eventsourcing import EventPublisher, StoredEvent

from .tables import outbox_table


class OutboxRelay:
    def __init__(self, session_factory: sessionmaker[Session], publisher: EventPublisher, batch_size: int = 100) -> None:
        self._session_factory = session_factory
        self._publisher = publisher
        self._batch_size = batch_size

    def run_once(self) -> int:
        """Publish one batch of pending events. Returns the number published."""
        session = self._session_factory()
        try:
            rows = session.execute(
                select(outbox_table)
                .where(outbox_table.c.published_at.is_(None))
                .order_by(outbox_table.c.id)
                .limit(self._batch_size)
                .with_for_update(skip_locked=True)
            ).mappings().all()

            if not rows:
                session.commit()
                return 0

            events = [
                StoredEvent(
                    stream_id=row["stream_id"],
                    aggregate_type=row["aggregate_type"],
                    version=0,  # version is not needed downstream; ordering is by MessageGroupId
                    event_type=row["event_type"],
                    event_id=row["event_id"],
                    occurred_at=row["occurred_at"],
                    payload=row["payload"],
                    tenant_id=row["tenant_id"],
                    correlation_id=row["correlation_id"],
                )
                for row in rows
            ]
            self._publisher.publish(events)

            ids = [row["id"] for row in rows]
            session.execute(
                outbox_table.update()
                .where(outbox_table.c.id.in_(ids))
                .values(published_at=text("now()"))
            )
            session.commit()
            return len(ids)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
