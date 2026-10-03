"""PostgresEventStore — the kernel `EventStore` port on PostgreSQL.

`append` writes the events AND their outbox rows in a SINGLE transaction — this is how we
avoid dual-write (the outbox and the event stream can never diverge). A separate relay
publishes the outbox to the bus. Optimistic concurrency is enforced by the
`UNIQUE(stream_id, version)` constraint (IntegrityError -> ConcurrencyError).

Wire the repository with outbox=None and publisher=None on the Postgres path; this store
handles outbox, and the relay handles publishing.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.shared.eventsourcing import ConcurrencyError, Snapshot, StoredEvent

from .engine import current_session
from .tables import events_table, outbox_table, snapshots_table


class PostgresEventStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def append(self, stream_id: str, expected_version: int, events: list[StoredEvent]) -> None:
        # Join an enclosing unit of work (FR-A4) if one is active — then another aggregate's
        # append in the same `atomic()` block commits together with this one. Otherwise own
        # the session + commit, exactly as before.
        ambient = current_session()
        session = ambient or self._session_factory()
        owns = ambient is None
        try:
            current = session.execute(
                select(func.coalesce(func.max(events_table.c.version), 0)).where(
                    events_table.c.stream_id == stream_id
                )
            ).scalar_one()
            if current != expected_version:
                raise ConcurrencyError(stream_id, expected_version, int(current))

            for event in events:
                row = {
                    "stream_id": event.stream_id,
                    "aggregate_type": event.aggregate_type,
                    "version": event.version,
                    "event_type": event.event_type,
                    "event_id": event.event_id,
                    "occurred_at": event.occurred_at,
                    "tenant_id": event.tenant_id,
                    "correlation_id": event.correlation_id,
                    "payload": dict(event.payload),
                }
                session.execute(events_table.insert().values(**row))
                session.execute(
                    outbox_table.insert().values(
                        event_id=event.event_id,
                        event_type=event.event_type,
                        stream_id=event.stream_id,
                        aggregate_type=event.aggregate_type,
                        tenant_id=event.tenant_id,
                        correlation_id=event.correlation_id,
                        payload=dict(event.payload),
                        occurred_at=event.occurred_at,
                    )
                )
            if owns:
                session.commit()
        except IntegrityError as exc:  # unique(stream_id, version) or event_id race
            if owns:
                session.rollback()
            raise ConcurrencyError(stream_id, expected_version, expected_version) from exc
        except Exception:
            if owns:
                session.rollback()
            raise
        finally:
            if owns:
                session.close()

    def load(self, stream_id: str, after_version: int = 0) -> list[StoredEvent]:
        session = self._session_factory()
        try:
            rows = session.execute(
                select(events_table)
                .where(events_table.c.stream_id == stream_id, events_table.c.version > after_version)
                .order_by(events_table.c.version)
            ).mappings().all()
        finally:
            session.close()
        return [
            StoredEvent(
                stream_id=row["stream_id"],
                aggregate_type=row["aggregate_type"],
                version=row["version"],
                event_type=row["event_type"],
                event_id=row["event_id"],
                occurred_at=row["occurred_at"],
                payload=row["payload"],
                tenant_id=row["tenant_id"],
                correlation_id=row["correlation_id"],
            )
            for row in rows
        ]

    def load_snapshot(self, stream_id: str) -> Snapshot | None:
        session = self._session_factory()
        try:
            row = session.execute(
                select(snapshots_table).where(snapshots_table.c.stream_id == stream_id)
            ).mappings().first()
        finally:
            session.close()
        if row is None:
            return None
        return Snapshot(stream_id=row["stream_id"], version=row["version"], state=row["state"], taken_at=row["taken_at"])

    def save_snapshot(self, snapshot: Snapshot) -> None:
        session = self._session_factory()
        try:
            session.execute(snapshots_table.delete().where(snapshots_table.c.stream_id == snapshot.stream_id))
            session.execute(
                snapshots_table.insert().values(
                    stream_id=snapshot.stream_id, version=snapshot.version, state=snapshot.state,
                    taken_at=snapshot.taken_at,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
