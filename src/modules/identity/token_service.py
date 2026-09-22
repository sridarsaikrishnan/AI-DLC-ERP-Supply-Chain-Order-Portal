"""TokenService — stateless signed tokens (P-U1-1, PyJWT).

Encodes userId/tenantId/role with expiry; verifies signature + expiry in-process.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import jwt

from ...shared.errors import AuthorizationError

_ALGO = "HS256"


def _secret() -> str:
    # Q7=A relaxes secret handling, but a real secret keeps tokens unforgeable.
    return os.environ.get("AUTH_SIGNING_SECRET", "dev-insecure-secret-change-me")


def _ttl_minutes() -> int:
    return int(os.environ.get("TOKEN_TTL_MINUTES", "60"))


def issue_token(user_id: str, tenant_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=_ttl_minutes())).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGO)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, _secret(), algorithms=[_ALGO])
    except jwt.ExpiredSignatureError as exc:
        raise AuthorizationError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthorizationError("invalid token") from exc
