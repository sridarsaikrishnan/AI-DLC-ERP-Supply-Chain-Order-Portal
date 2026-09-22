"""Identity ORM tables (U1). Passwords stored as-is for MVP (Q7=A, flagged)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..foundation.persistence.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="CLIENT_USER")
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")


class CredentialRow(Base):
    __tablename__ = "credentials"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    password: Mapped[str] = mapped_column(String, nullable=False)  # as-is (Q7=A)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    throttled_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MfaEnrollmentRow(Base):
    __tablename__ = "mfa_enrollments"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    totp_secret: Mapped[str] = mapped_column(String, nullable=False)
    enrolled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
