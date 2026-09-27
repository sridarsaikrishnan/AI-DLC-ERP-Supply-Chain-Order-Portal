"""Outbox port + in-memory implementation.

The transactional outbox is written in the SAME transaction as the events (no dual
write). A relay later reads it and publishes to the bus. Production binds a Postgres
outbox; tests/local use the in-memory one.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .events import StoredEvent


@runtime_checkable
class Outbox(Protocol):
    def add(self, events: list[StoredEvent]) -> None: ...


class InMemoryOutbox:
    def __init__(self) -> None:
        self.records: list[StoredEvent] = []

    def add(self, events: list[StoredEvent]) -> None:
        self.records.extend(events)
