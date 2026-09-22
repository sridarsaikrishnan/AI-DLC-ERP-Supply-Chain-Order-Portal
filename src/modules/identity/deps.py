"""FastAPI dependencies for auth (LC-U1-5).

- current_context: resolves SecurityContext from the bearer token and binds it so
  U0 tenant-scoped repositories work fail-closed.
- require_role: authorization guard.

Auth failures are surfaced as proper HTTP 401/403 responses (not 500).
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from ..foundation.context.security_context import SecurityContext, set_context
from ...shared.errors import AuthorizationError
from .service import AuthService


def current_context(authorization: str | None = Header(default=None)) -> SecurityContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        ctx = AuthService.resolve_context(token)
    except AuthorizationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    set_context(ctx)  # bind for U0 tenant scoping on this request
    return ctx


def require_role(required_role: str):
    def _guard(ctx: SecurityContext = Depends(current_context)) -> SecurityContext:
        try:
            AuthService.authorize(ctx, required_role)
        except AuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        return ctx

    return _guard
