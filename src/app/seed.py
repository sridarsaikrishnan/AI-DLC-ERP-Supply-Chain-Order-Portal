"""Local bootstrap: create tables and seed demo data for the SQLite PoC.

Only used when running against SQLite (no migrations pipeline). For PostgreSQL the
migrations/*.sql files handle schema + seed instead.
"""

from __future__ import annotations

from ..modules.foundation.persistence.database import SessionLocal, _database_url, create_all
from ..modules.foundation.persistence.tables import ErpInstanceRow
from ..modules.identity.models import CredentialRow, MfaEnrollmentRow, UserRow  # noqa: F401  (register tables)


def is_sqlite() -> bool:
    return _database_url().startswith("sqlite")


def seed_local() -> None:
    """Create tables and insert demo tenant/users if missing (SQLite PoC only)."""
    create_all()
    session = SessionLocal()
    try:
        # seed users (mirrors migrations/002_identity.sql)
        if session.get(UserRow, "user-admin") is None:
            session.add(UserRow(id="user-admin", username="admin", tenant_id="tenant-demo", role="ADMIN", status="active"))
            session.add(CredentialRow(user_id="user-admin", password="admin123", failed_attempts=0))
        if session.get(UserRow, "user-client") is None:
            session.add(UserRow(id="user-client", username="client", tenant_id="tenant-demo", role="CLIENT_USER", status="active"))
            session.add(CredentialRow(user_id="user-client", password="client123", failed_attempts=0))
        session.commit()
    finally:
        session.close()
