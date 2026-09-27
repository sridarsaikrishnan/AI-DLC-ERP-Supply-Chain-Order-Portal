"""Kernel tests: append/replay, optimistic concurrency, snapshots, outbox/publish,
and serialization errors. Dependency-free (no pytest plugins required)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from src.shared.eventsourcing import (
    Aggregate,
    AggregateNotFound,
    CollectingPublisher,
    ConcurrencyError,
    DomainEvent,
    EventSourcedRepository,
    InMemoryEventStore,
    InMemoryOutbox,
    StoredEvent,
    UnhandledEvent,
    UnknownEventType,
    event_from_stored,
    register_event,
)


# --- a sample event-sourced aggregate used only by these tests ---
@register_event
@dataclass(frozen=True, kw_only=True)
class Created(DomainEvent):
    name: str


@register_event
@dataclass(frozen=True, kw_only=True)
class Incremented(DomainEvent):
    by: int


class Counter(Aggregate):
    aggregate_type = "Counter"

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.name = ""
        self.total = 0

    # behavior (invariants live here, not in a service)
    @classmethod
    def create(cls, id: str, name: str) -> "Counter":
        c = cls(id)
        c.emit(Created(name=name))
        return c

    def increment(self, by: int) -> None:
        if by <= 0:
            raise ValueError("increment must be positive")
        self.emit(Incremented(by=by))

    # state transitions (pure applies)
    def _apply_Created(self, e: Created) -> None:
        self.name = e.name

    def _apply_Incremented(self, e: Incremented) -> None:
        self.total += e.by

    # snapshot support
    def snapshot_state(self) -> dict[str, Any]:
        return {"name": self.name, "total": self.total}

    def restore(self, state: dict[str, Any]) -> None:
        self.name = state["name"]
        self.total = state["total"]


def _repo(store: InMemoryEventStore, **kw: Any) -> EventSourcedRepository[Counter]:
    return EventSourcedRepository(store, Counter, **kw)


def test_save_then_replay_rebuilds_state() -> None:
    store = InMemoryEventStore()
    repo = _repo(store)
    c = Counter.create("c1", "widget")
    c.increment(5)
    c.increment(2)
    repo.save(c)

    loaded = repo.get("c1")
    assert loaded.name == "widget"
    assert loaded.total == 7
    assert loaded.version == 3
    assert not loaded.has_pending


def test_versions_are_contiguous_and_metadata_stamped() -> None:
    store = InMemoryEventStore()
    repo = _repo(store, metadata_provider=lambda: ("tnt_1", "corr_1"))
    c = Counter.create("c1", "x")
    c.increment(1)
    stored = repo.save(c)

    assert [e.version for e in stored] == [1, 2]
    assert all(e.tenant_id == "tnt_1" and e.correlation_id == "corr_1" for e in stored)
    assert stored[0].event_type == "Created"


def test_optimistic_concurrency_conflict() -> None:
    store = InMemoryEventStore()
    repo = _repo(store)
    repo.save(Counter.create("c1", "x"))

    a = repo.get("c1")
    b = repo.get("c1")
    a.increment(1)
    b.increment(1)
    repo.save(a)
    with pytest.raises(ConcurrencyError):
        repo.save(b)


def test_outbox_and_publisher_receive_events() -> None:
    store = InMemoryEventStore()
    outbox = InMemoryOutbox()
    publisher = CollectingPublisher()
    repo = _repo(store, outbox=outbox, publisher=publisher)

    c = Counter.create("c1", "x")
    c.increment(3)
    repo.save(c)

    assert len(outbox.records) == 2
    assert len(publisher.published) == 2
    assert [e.event_type for e in publisher.published] == ["Created", "Incremented"]


def test_snapshot_used_on_reload() -> None:
    store = InMemoryEventStore()
    repo = _repo(store, snapshot_every=2)
    c = Counter.create("c1", "x")  # version 1
    c.increment(10)  # version 2 -> snapshot taken
    repo.save(c)

    assert store.load_snapshot("c1") is not None
    loaded = repo.get("c1")
    assert loaded.total == 10
    assert loaded.version == 2


def test_get_missing_aggregate_raises() -> None:
    with pytest.raises(AggregateNotFound):
        _repo(InMemoryEventStore()).get("nope")


def test_unhandled_event_raises() -> None:
    @register_event
    @dataclass(frozen=True, kw_only=True)
    class Unexpected(DomainEvent):
        pass

    c = Counter("c1")
    with pytest.raises(UnhandledEvent):
        c.apply(Unexpected())


def test_unknown_event_type_on_deserialize() -> None:
    bogus = StoredEvent(
        stream_id="c1",
        aggregate_type="Counter",
        version=1,
        event_type="NeverRegistered",
        event_id="e1",
        occurred_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        payload={},
    )
    with pytest.raises(UnknownEventType):
        event_from_stored(bogus)


def test_events_are_immutable() -> None:
    e = Incremented(by=1)
    with pytest.raises(Exception):
        e.by = 2  # type: ignore[misc]
