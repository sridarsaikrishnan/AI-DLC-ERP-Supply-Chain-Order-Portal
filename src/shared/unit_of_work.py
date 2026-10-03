"""Unit-of-work port — lets a service commit writes to more than one aggregate in a
single transaction (Increment 5, FR-A4: a shipment and the order quantity update land
together or not at all).

Framework-free. The in-memory implementation is a no-op (the in-memory event store can't
partially fail across two appends); the Postgres implementation lives in
`src/shared/persistence/engine.py` and makes `PostgresEventStore.append` join one ambient
session.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol, runtime_checkable


@runtime_checkable
class UnitOfWork(Protocol):
    def atomic(self) -> AtomicContext: ...


class AtomicContext(Protocol):
    def __enter__(self) -> None: ...
    def __exit__(self, *exc: object) -> bool | None: ...


class NullUnitOfWork:
    """No-op UoW for the in-memory profile and tests."""

    @contextmanager
    def atomic(self) -> Iterator[None]:
        yield
