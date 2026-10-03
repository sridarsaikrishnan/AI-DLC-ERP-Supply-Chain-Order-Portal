"""Per-connection advisory lock so two `worker` replicas never sweep the same ERP
connection concurrently — closes the known gap in ADR-0007/ADR-0010 (today, N replicas
each sweep every connection on the same timer, multiplying real ERP API load by N).

Session-scoped: `pg_advisory_lock` ties the lock to the DB session that acquired it, so
the lock is held for exactly the duration of one connection's sweep, on a dedicated
short-lived session, then explicitly released — never left to an implicit session-close.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol

from sqlalchemy import text


class ConnectionLock(Protocol):
    def try_acquire(self, connection_id: str) -> Any: ...  # context manager yielding bool


class PostgresConnectionLock:
    _NAMESPACE = "reconcile"

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    @contextmanager
    def try_acquire(self, connection_id: str) -> Iterator[bool]:
        session = self._session_factory()
        try:
            acquired = bool(
                session.execute(
                    text("SELECT pg_try_advisory_lock(hashtext(:ns), hashtext(:key))"),
                    {"ns": self._NAMESPACE, "key": connection_id},
                ).scalar()
            )
            try:
                yield acquired
            finally:
                if acquired:
                    session.execute(
                        text("SELECT pg_advisory_unlock(hashtext(:ns), hashtext(:key))"),
                        {"ns": self._NAMESPACE, "key": connection_id},
                    )
                    session.commit()
        finally:
            session.close()
