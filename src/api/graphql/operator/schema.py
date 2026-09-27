"""Operator GraphQL schema. Requires the OPERATOR role; may expose ERP identity."""

from __future__ import annotations

import strawberry
from strawberry.extensions import QueryDepthLimiter
from strawberry.types import Info

from src.modules.ordering.projections.read_models import OperatorOrderView

from ..context import GraphQLContext
from .types import OperatorOrder, OperatorOrderLineType


def _to_gql(view: OperatorOrderView) -> OperatorOrder:
    return OperatorOrder(
        order_id=view.order_id,
        tenant_id=view.tenant_id,
        client_reference=view.client_reference,
        status=view.status,
        owning_connection_id=view.owning_connection_id,
        erp_order_id=view.erp_order_id,
        lines=[
            OperatorOrderLineType(product_key=l.product_key, quantity=l.quantity, unit_of_measure=l.unit_of_measure)
            for l in view.lines
        ],
    )


@strawberry.type
class Query:
    @strawberry.field
    def order(self, info: Info[GraphQLContext, None], order_id: str) -> OperatorOrder | None:
        ctx = info.context
        ctx.require_role("OPERATOR")
        view = ctx.container.projections.get_operator_view(order_id)
        return _to_gql(view) if view else None


def build_operator_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=[QueryDepthLimiter(max_depth=10)])
