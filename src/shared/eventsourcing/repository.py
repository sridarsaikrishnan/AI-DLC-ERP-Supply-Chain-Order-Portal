"""Generic event-sourced repository: rebuild by replay, save by append.

Wiring, not domain logic. A module composes it with an aggregate class, a store, and
(optionally) an outbox + publisher + snapshot cadence.

`save` order matters: append to the store first (optimistic-concurrency gate), then
record to the outbox / publish. In production the outbox add happens in the same DB
transaction as the append (the Postgres store adapter owns that transaction).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

from .aggregate import Aggregate
from .errors import AggregateNotFound
from .events import StoredEvent
from .outbox import Outbox
from .publisher import EventPublisher
from .serialization import event_from_stored, event_type_name, to_payload
from .snapshots import Snapshot
from .store import EventStore

A = TypeVar("A", bound=Aggregate)

# Returns (tenant_id, correlation_id) for stamping onto outgoing events.
MetadataProvider = Callable[[], tuple[str | None, str | None]]


class EventSourcedRepository(Generic[A]):
    def __init__(
        self,
        store: EventStore,
        aggregate_cls: type[A],
        *,
        outbox: Outbox | None = None,
        publisher: EventPublisher | None = None,
        metadata_provider: MetadataProvider | None = None,
        snapshot_every: int | None = None,
    ) -> None:
        self._store = store
        self._aggregate_cls = aggregate_cls
        self._outbox = outbox
        self._publisher = publisher
        self._metadata = metadata_provider
        self._snapshot_every = snapshot_every

    def get(self, aggregate_id: str) -> A:
        snapshot = self._store.load_snapshot(aggregate_id)
        aggregate: A | None = None
        after = 0
        if snapshot is not None:
            aggregate = self._aggregate_cls(aggregate_id)
            aggregate.restore(snapshot.state)
            aggregate.version = snapshot.version
            after = snapshot.version

        stored = self._store.load(aggregate_id, after_version=after)
        if aggregate is None:
            if not stored:
                raise AggregateNotFound(aggregate_id)
            aggregate = self._aggregate_cls(aggregate_id)

        for record in stored:
            aggregate.apply(event_from_stored(record))
            aggregate.version += 1
        return aggregate

    def save(self, aggregate: A) -> list[StoredEvent]:
        pending = aggregate.collect_events()
        if not pending:
            return []

        expected = aggregate.version - len(pending)
        tenant_id, correlation_id = self._metadata() if self._metadata else (None, None)

        stored: list[StoredEvent] = []
        version = expected
        for event in pending:
            version += 1
            stored.append(
                StoredEvent(
                    stream_id=aggregate.id,
                    aggregate_type=aggregate.aggregate_type,
                    version=version,
                    event_type=event_type_name(event),
                    event_id=event.event_id,
                    occurred_at=event.occurred_at,
                    payload=to_payload(event),
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                )
            )

        self._store.append(aggregate.id, expected, stored)
        if self._outbox is not None:
            self._outbox.add(stored)
        if self._publisher is not None:
            self._publisher.publish(stored)
        self._maybe_snapshot(aggregate)
        return stored

    def _maybe_snapshot(self, aggregate: A) -> None:
        if not self._snapshot_every:
            return
        if aggregate.version % self._snapshot_every != 0:
            return
        state = aggregate.snapshot_state()
        if state is None:
            return
        self._store.save_snapshot(
            Snapshot(stream_id=aggregate.id, version=aggregate.version, state=state)
        )
