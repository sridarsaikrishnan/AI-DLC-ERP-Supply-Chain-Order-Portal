"""Database engine/session setup (LC-1).

SQLAlchemy engine + session factory. SQLAlchemy parameterizes queries by default
(partial mitigation for NFR-U0-SEC-3, which was left unmandated per Q7=A).

The engine is created lazily (not at import time) so that importing models/services
does not require a live database or a specific driver. This makes the code testable
and lets the app run against SQLite for local/PoC use when DATABASE_URL is unset.

Note on the DB-backed queue: `SELECT ... FOR UPDATE SKIP LOCKED` is a PostgreSQL
feature. On SQLite (local single-process PoC) the claim still functions for a single
worker; use PostgreSQL for the multi-replica deployment described in the design.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    # Default to a local SQLite file so the app runs with no external DB.
    # Set DATABASE_URL to a postgresql+psycopg2://... URL for the real deployment.
    return os.environ.get("DATABASE_URL", "sqlite:///./portal_local.db")


_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = _database_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, pool_pre_ping=True, future=True, connect_args=connect_args)
    return _engine


def _session_factory() -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False, future=True
        )
    return _SessionFactory


def SessionLocal():
    """Create a new Session (callable, matches prior usage `SessionLocal()`)."""
    return _session_factory()()


def create_all() -> None:
    """Create tables from ORM metadata. Imports table modules so they register on Base."""
    # Import here to avoid circulars and ensure all tables are registered.
    from . import tables  # noqa: F401
    try:
        from ...identity import models as _identity_models  # noqa: F401
    except Exception:  # identity may not be present in every context
        pass
    Base.metadata.create_all(get_engine())


def get_session():
    """Yield a session (FastAPI dependency style)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
