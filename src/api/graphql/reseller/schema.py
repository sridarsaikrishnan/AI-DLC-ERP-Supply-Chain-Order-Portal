"""Reseller GraphQL schema: queries over projections, mutations mapped to commands.

Depth/complexity limits are applied; introspection is disabled in production (api/app.py).
Every resolver is tenant-scoped via the context.
"""

from __future__ import annotations

import strawberry
from strawberry.extensions import QueryDepthLimiter
from strawberry.types import Info

from src.modules.ordering.domain.models import OrderLine
from src.modules.ordering.projections.read_models import ResellerOrderView
from src.shared.types import OrderId, TenantId

from ..context import GraphQLContext
from .types import OrderLineInput, OrderLineType, ResellerOrder, TimelineEntryType


def _to_gql(view: ResellerOrderView) -> ResellerOrder:
    return ResellerOrder(
        order_id=view.order_id,
        client_reference=view.client_reference,
        status=view.status,
        lines=[
            OrderLineType(product_key=l.product_key, quantity=l.quantity, unit_of_measure=l.unit_of_measure)
            for l in view.lines
        ],
        timeline=[TimelineEntryType(status=t.status, occurred_at=t.occurred_at) for t in view.timeline],
    )


@strawberry.type
class Query:
    @strawberry.field
    def orders(self, info: Info[GraphQLContext, None]) -> list[ResellerOrder]:
        ctx = info.context
        return [_to_gql(v) for v in ctx.container.projections.list_reseller_views(ctx.tenant_id)]

    @strawberry.field
    def order(self, info: Info[GraphQLContext, None], order_id: str) -> ResellerOrder | None:
        ctx = info.context
        view = ctx.container.projections.get_reseller_view(ctx.tenant_id, order_id)
        return _to_gql(view) if view else None


@strawberry.type
class Mutation:
    @strawberry.mutation
    def place_order(
        self, info: Info[GraphQLContext, None], client_reference: str, lines: list[OrderLineInput]
    ) -> str:
        ctx = info.context
        order_id = ctx.container.order_service.place_order(
            tenant_id=TenantId(ctx.tenant_id),
            client_reference=client_reference,
            lines=[OrderLine(li.product_key, li.quantity, li.unit_of_measure) for li in lines],
        )
        # Memory profile drains inline; postgres profile no-ops here and the worker
        # drains the queues asynchronously, so this call returns before delivery.
        ctx.container.drain()
        return order_id

    @strawberry.mutation
    def cancel_order(self, info: Info[GraphQLContext, None], order_id: str, reason: str) -> bool:
        ctx = info.context
        ctx.container.order_service.cancel_order(OrderId(order_id), reason)
        ctx.container.drain()
        return True


def build_reseller_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, mutation=Mutation, extensions=[QueryDepthLimiter(max_depth=10)])
