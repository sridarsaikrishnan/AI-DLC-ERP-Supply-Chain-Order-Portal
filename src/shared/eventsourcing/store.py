"""Event store port + an in-memory implementation.

The port is the seam: the in-memory store powers unit tests and simple local runs; a
Postgres-backed adapter (Phase 2) implements the same protocol without touching the
domain. `append` enforces optimistic concurrency via the expected version.
"""

from __future__ import annotations

import threading
from typing import Protocol, runtime_checkable

from .errors import ConcurrencyError
from .events import StoredEvent
from .snapshots import Snapshot


@runtime_checkable
class EventStore(Protocol):
    def append(self, stream_id: str, expected_version: int, events: list[StoredEvent]) -> None: ...
    def load(self, stream_id: str, after_version: int = 0) -> list[StoredEvent]: ...
    def load_snapshot(self, stream_id: str) -> Snapshot | None: ...
    def save_snapshot(self, snapshot: Snapshot) -> None: ...


class InMemoryEventStore:
    """Thread-safe, dependency-free store for tests and simple local runs.

    Streams are 1-based, contiguous: the i-th appended event has version i+1.
    """

    def __init__(self) -> None:
        self._streams: dict[str, list[StoredEvent]] = {}
        self._snapshots: dict[str, Snapshot] = {}
        self._lock = threading.RLock()

    def append(self, stream_id: str, expected_version: int, events: list[StoredEvent]) -> None:
        with self._lock:
            current = self._streams.get(stream_id, [])
            if len(current) != expected_version:
                raise ConcurrencyError(stream_id, expected_version, len(current))
            self._streams[stream_id] = current + list(events)

    def load(self, stream_id: str, after_version: int = 0) -> list[StoredEvent]:
        with self._lock:
            return list(self._streams.get(stream_id, [])[after_version:])

    def load_snapshot(self, stream_id: str) -> Snapshot | None:
        with self._lock:
            return self._snapshots.get(stream_id)

    def save_snapshot(self, snapshot: Snapshot) -> None:
        with self._lock:
            self._snapshots[snapshot.stream_id] = snapshot
