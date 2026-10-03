"""Tests for the in-memory message bus: filtering, ordering, dedup, retry -> DLQ."""

from __future__ import annotations

from datetime import UTC, datetime

from src.shared.eventsourcing import StoredEvent
from src.shared.messaging import InMemoryMessageBus


def _event(
    event_type: str, stream_id: str = "s1", version: int = 1, event_id: str | None = None
) -> StoredEvent:
    return StoredEvent(
        stream_id=stream_id,
        aggregate_type="T",
        version=version,
        event_type=event_type,
        event_id=event_id or f"{event_type}-{version}",
        occurred_at=datetime.now(UTC),
        payload={},
    )


def test_filter_policy_routes_only_matching_events() -> None:
    bus = InMemoryMessageBus()
    got_a: list[str] = []
    got_all: list[str] = []
    bus.subscribe("only-a", lambda e: got_a.append(e.event_type), event_types={"A"})
    bus.subscribe("all", lambda e: got_all.append(e.event_type))

    bus.deliver([_event("A", version=1), _event("B", version=2)])

    assert got_a == ["A"]
    assert got_all == ["A", "B"]


def test_delivery_preserves_enqueue_order() -> None:
    bus = InMemoryMessageBus()
    seen: list[int] = []
    bus.subscribe("c", lambda e: seen.append(e.version))
    bus.deliver([_event("E", version=1), _event("E", version=2), _event("E", version=3)])
    assert seen == [1, 2, 3]


def test_consumer_dedup_processes_once() -> None:
    bus = InMemoryMessageBus()
    calls: list[str] = []
    bus.subscribe("c", lambda e: calls.append(e.event_id))
    dup = _event("E", event_id="same")
    bus.deliver([dup, dup])
    assert calls == ["same"]
    assert bus.processed_count("c") == 1


def test_failing_handler_retries_then_dead_letters() -> None:
    bus = InMemoryMessageBus()

    def always_fail(_e: StoredEvent) -> None:
        raise RuntimeError("boom")

    bus.subscribe("c", always_fail, max_receive=3)
    bus.deliver([_event("E", event_id="x")])

    dlq = bus.dead_letters("c")
    assert len(dlq) == 1 and dlq[0].event_id == "x"
    assert bus.processed_count("c") == 0


def test_transient_failure_then_success_is_not_dead_lettered() -> None:
    bus = InMemoryMessageBus()
    attempts = {"n": 0}

    def flaky(_e: StoredEvent) -> None:
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RuntimeError("transient")

    bus.subscribe("c", flaky, max_receive=5)
    bus.deliver([_event("E", event_id="y")])

    assert bus.dead_letters("c") == []
    assert bus.processed_count("c") == 1
    assert attempts["n"] == 2
