"""SecurityContext and propagation (LC-3, BR-2, BR-3.4).

The SecurityContext carries the authenticated user's identity, tenant, and roles.
It is stored in a context variable so tenant-scoped repositories can read it
(fail-closed if absent). Workers reconstruct a context from a job's tenant id.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SecurityContext:
    user_id: str | None
    tenant_id: str
    roles: tuple[str, ...] = field(default_factory=tuple)

    def has_role(self, role: str) -> bool:
        return role in self.roles


_current: ContextVar[SecurityContext | None] = ContextVar("security_context", default=None)


def get_context() -> SecurityContext | None:
    return _current.get()


def set_context(ctx: SecurityContext | None) -> None:
    _current.set(ctx)


@contextmanager
def use_context(ctx: SecurityContext):
    """Bind a SecurityContext for the duration of a block (used by workers per job)."""
    token = _current.set(ctx)
    try:
        yield ctx
    finally:
        _current.reset(token)


def context_from_tenant(tenant_id: str, user_id: str | None = None, roles: tuple[str, ...] = ()) -> SecurityContext:
    """Reconstruct a minimal context for async job processing (BR-3.4)."""
    return SecurityContext(user_id=user_id, tenant_id=tenant_id, roles=roles)
