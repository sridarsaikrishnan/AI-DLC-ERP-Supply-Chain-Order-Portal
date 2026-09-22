"""Tenant-scoped order repositories (LC-U2-2), built on U0's TenantScopedRepository.

These enforce tenant isolation (fail-closed) via the U0 base for order reads,
and use explicit tenant checks for inserts/history.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..foundation.context.security_context import get_context
from ..foundation.persistence.tables import OrderRow, OrderStatusHistoryRow
from ..foundation.persistence.tenant_repository import TenantScopedRepository
from ...shared.errors import AuthorizationError, NotFoundError


class OrderRepository(TenantScopedRepository[OrderRow]):
    model = OrderRow

    def create(self, order: OrderRow) -> OrderRow:
        return self.add(order)  # base stamps tenant_id + fail-closed


class StatusHistoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def _tenant(self) -> str:
        ctx = get_context()
        if ctx is None or not ctx.tenant_id:
            raise AuthorizationError("no tenant context")
        return ctx.tenant_id

    def for_order(self, order_id: str) -> list[OrderStatusHistoryRow]:
        tenant_id = self._tenant()
        stmt = (
            select(OrderStatusHistoryRow)
            .where(
                OrderStatusHistoryRow.order_id == order_id,
                OrderStatusHistoryRow.tenant_id == tenant_id,
            )
            .order_by(OrderStatusHistoryRow.occurred_at)
        )
        return list(self.session.execute(stmt).scalars().all())
