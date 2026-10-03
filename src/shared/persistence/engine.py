"""Engine/session factory + per-request tenant binding for row-level security."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.engine import Engine

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://portal:portal@localhost:5432/portal"
    )


def get_engine(url: str | None = None) -> Engine:
    """`url` (e.g. `Settings.database_url`) is only honored on the first call that
    creates the engine — it's a process-wide singleton, matching the sessionmaker below."""
    global _engine
    if _engine is None:
        _engine = create_engine(url or database_url(), pool_pre_ping=True, future=True)
    return _engine


def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(url), autoflush=False, expire_on_commit=False, future=True
        )
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def bind_tenant(session: Session, tenant_id: str) -> None:
    """Set the RLS tenant for the current transaction (SECURITY-08 defense in depth)."""
    session.execute(text("SET LOCAL app.tenant_id = :tenant"), {"tenant": tenant_id})
