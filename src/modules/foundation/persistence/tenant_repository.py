"""Tenant-scoped repository base (LC-1, P-4, BR-2).

Enforces tenant isolation for tenant-owned aggregates:
- Automatic tenant_id filter on every query (BR-2.1)
- Fail-closed if no SecurityContext / tenant_id is present (BR-2.2)
- Cross-tenant single-record access returns NotFound, no existence leak (BR-2.3)
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..context.security_context import get_context
from ....shared.errors import AuthorizationError, NotFoundError

T = TypeVar("T")


class TenantScopedRepository(Generic[T]):
    """Base for repositories over tenant-owned tables. Subclasses set `model` and expect
    the model to have a `tenant_id` column."""

    model: type

    def __init__(self, session: Session):
        self.session = session

    def _require_tenant_id(self) -> str:
        ctx = get_context()
        if ctx is None or not ctx.tenant_id:
            # Fail-closed: never default to "all tenants" (BR-2.2)
            raise AuthorizationError("No security context / tenant id present for tenant-scoped access")
        return ctx.tenant_id

    def add(self, entity: T) -> T:
        tenant_id = self._require_tenant_id()
        # Stamp tenant id defensively
        setattr(entity, "tenant_id", tenant_id)
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, entity_id) -> T:
        tenant_id = self._require_tenant_id()
        stmt = select(self.model).where(
            self.model.id == entity_id,
            self.model.tenant_id == tenant_id,
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        if result is None:
            # Also covers cross-tenant access (BR-2.3): treated as not found
            raise NotFoundError(f"{self.model.__name__} {entity_id} not found")
        return result

    def list(self) -> list[T]:
        tenant_id = self._require_tenant_id()
        stmt = select(self.model).where(self.model.tenant_id == tenant_id)
        return list(self.session.execute(stmt).scalars().all())
