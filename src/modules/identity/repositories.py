"""Identity repositories (LC-U1-4). Use the U0 SQLAlchemy session.

These are identity/platform data (keyed by user), not tenant-scoped in the U0
row-filter sense — a user IS the source of tenant context.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CredentialRow, MfaEnrollmentRow, UserRow


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def by_username(self, username: str) -> UserRow | None:
        return self.session.execute(
            select(UserRow).where(UserRow.username == username)
        ).scalar_one_or_none()


class CredentialRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, user_id: str) -> CredentialRow | None:
        return self.session.get(CredentialRow, user_id)

    def save(self, cred: CredentialRow) -> None:
        self.session.add(cred)
        self.session.flush()


class MfaRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, user_id: str) -> MfaEnrollmentRow | None:
        return self.session.get(MfaEnrollmentRow, user_id)
