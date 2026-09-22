"""AuthService — login, MFA, context resolution, authorization (BR-U1-1..6).

Passwords compared as-is (Q7=A). Soft throttle via credential counters (BR-U1-3).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..foundation.context.security_context import SecurityContext
from ...shared.errors import AuthorizationError
from . import token_service, totp_service
from .repositories import CredentialRepository, MfaRepository, UserRepository


def _max_failed() -> int:
    return int(os.environ.get("LOGIN_MAX_FAILED_ATTEMPTS", "5"))


def _throttle_seconds() -> int:
    return int(os.environ.get("LOGIN_THROTTLE_SECONDS", "300"))


@dataclass
class LoginOutcome:
    token: str | None = None
    mfa_required: bool = False
    user_id: str | None = None


class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)
        self.creds = CredentialRepository(session)
        self.mfa = MfaRepository(session)

    def login(self, username: str, password: str) -> LoginOutcome:
        user = self.users.by_username(username)
        # Generic error, no existence disclosure (BR-U1-1.2)
        if user is None or user.status != "active":
            raise AuthorizationError("invalid credentials")

        cred = self.creds.get(user.id)
        if cred is None:
            raise AuthorizationError("invalid credentials")

        now = datetime.now(timezone.utc)
        if cred.throttled_until and cred.throttled_until > now:
            raise AuthorizationError("account temporarily throttled")

        if cred.password != password:  # as-is compare (Q7=A)
            cred.failed_attempts += 1
            if cred.failed_attempts >= _max_failed():
                cred.throttled_until = now + timedelta(seconds=_throttle_seconds())
                cred.failed_attempts = 0
            self.creds.save(cred)
            raise AuthorizationError("invalid credentials")

        # success: reset throttle
        cred.failed_attempts = 0
        cred.throttled_until = None
        self.creds.save(cred)

        enrollment = self.mfa.get(user.id)
        if enrollment and enrollment.enrolled:
            return LoginOutcome(mfa_required=True, user_id=user.id)

        return LoginOutcome(token=token_service.issue_token(user.id, user.tenant_id, user.role))

    def verify_mfa(self, user_id: str, code: str) -> LoginOutcome:
        from .models import UserRow

        user = self.session.get(UserRow, user_id)
        if user is None or user.status != "active":
            raise AuthorizationError("invalid credentials")
        enrollment = self.mfa.get(user_id)
        if enrollment is None or not totp_service.verify_totp(enrollment.totp_secret, code):
            raise AuthorizationError("invalid mfa code")
        return LoginOutcome(token=token_service.issue_token(user.id, user.tenant_id, user.role))

    @staticmethod
    def resolve_context(token: str) -> SecurityContext:
        claims = token_service.verify_token(token)
        return SecurityContext(
            user_id=claims.get("sub"),
            tenant_id=claims["tenant_id"],
            roles=(claims.get("role", "CLIENT_USER"),),
        )

    @staticmethod
    def authorize(ctx: SecurityContext, required_role: str) -> None:
        # ADMIN satisfies any requirement; CLIENT_USER satisfies CLIENT_USER (BR-U1-5)
        if ctx.has_role("ADMIN"):
            return
        if required_role == "CLIENT_USER" and ctx.has_role("CLIENT_USER"):
            return
        raise AuthorizationError("insufficient role")
