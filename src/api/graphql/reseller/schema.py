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
from src.modules.webhooks_outbound.application.service import WebhookEndpointService
from src.modules.webhooks_outbound.domain.models import WebhookDelivery, WebhookEndpoint
from src.shared.money import Money
from src.shared.types import OrderId, TenantId, WebhookEndpointId

from ..context import GraphQLContext
from .types import (
    MoneyType,
    OrderLineInput,
    OrderLineType,
    ResellerOrder,
    TimelineEntryType,
    WebhookDeliveryType,
    WebhookEndpointCreatedType,
    WebhookEndpointType,
)


def _money_to_gql(money: Money | None) -> MoneyType | None:
    return None if money is None else MoneyType(amount=float(money.amount), currency=money.currency)


def _to_gql(view: ResellerOrderView) -> ResellerOrder:
    return ResellerOrder(
        order_id=view.order_id,
        client_reference=view.client_reference,
        status=view.status,
        lines=[
            OrderLineType(
                product_key=l.product_key,
                quantity=l.quantity,
                unit_of_measure=l.unit_of_measure,
                unit_price=_money_to_gql(l.unit_price),
                line_total=_money_to_gql(l.line_total),
            )
            for l in view.lines
        ],
        timeline=[TimelineEntryType(status=t.status, occurred_at=t.occurred_at) for t in view.timeline],
        subtotal=_money_to_gql(view.subtotal),
    )


def _endpoint_to_gql(endpoint: WebhookEndpoint) -> WebhookEndpointType:
    return WebhookEndpointType(
        endpoint_id=str(endpoint.endpoint_id),
        name=endpoint.name,
        url=endpoint.url,
        event_types=list(endpoint.event_types) if endpoint.event_types is not None else None,
        is_active=endpoint.is_active,
    )


def _delivery_to_gql(delivery: WebhookDelivery) -> WebhookDeliveryType:
    return WebhookDeliveryType(
        delivery_id=delivery.delivery_id,
        endpoint_id=str(delivery.endpoint_id),
        order_id=delivery.order_id,
        event_type=delivery.event_type,
        occurred_at=delivery.occurred_at.isoformat(),
        status=delivery.status.value,
        attempts=delivery.attempts,
        last_response=delivery.last_response,
        payload=delivery.payload,
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

    @strawberry.field
    def webhook_endpoints(self, info: Info[GraphQLContext, None]) -> list[WebhookEndpointType]:
        ctx = info.context
        return [
            _endpoint_to_gql(e) for e in ctx.container.webhook_endpoints.list_by_tenant(TenantId(ctx.tenant_id))
        ]

    @strawberry.field
    def delivery_log(self, info: Info[GraphQLContext, None]) -> list[WebhookDeliveryType]:
        """Every webhook delivery attempt for this tenant — what got sent to your
        endpoints, and whether it arrived."""
        ctx = info.context
        return [
            _delivery_to_gql(d) for d in ctx.container.webhook_deliveries.list_by_tenant(TenantId(ctx.tenant_id))
        ]


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

    @strawberry.mutation
    def register_webhook_endpoint(
        self, info: Info[GraphQLContext, None], name: str, url: str, event_types: list[str] | None = None
    ) -> WebhookEndpointCreatedType:
        ctx = info.context
        service = WebhookEndpointService(ctx.container.webhook_endpoints, ctx.container.secrets)
        endpoint, raw_secret = service.register(
            tenant_id=TenantId(ctx.tenant_id),
            name=name,
            url=url,
            event_types=frozenset(event_types) if event_types else None,
        )
        return WebhookEndpointCreatedType(endpoint=_endpoint_to_gql(endpoint), signing_secret=raw_secret)

    @strawberry.mutation
    def pause_webhook_endpoint(self, info: Info[GraphQLContext, None], endpoint_id: str) -> WebhookEndpointType:
        ctx = info.context
        service = WebhookEndpointService(ctx.container.webhook_endpoints, ctx.container.secrets)
        return _endpoint_to_gql(service.pause(WebhookEndpointId(endpoint_id), tenant_id=TenantId(ctx.tenant_id)))

    @strawberry.mutation
    def resume_webhook_endpoint(self, info: Info[GraphQLContext, None], endpoint_id: str) -> WebhookEndpointType:
        ctx = info.context
        service = WebhookEndpointService(ctx.container.webhook_endpoints, ctx.container.secrets)
        return _endpoint_to_gql(service.resume(WebhookEndpointId(endpoint_id), tenant_id=TenantId(ctx.tenant_id)))


def build_reseller_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, mutation=Mutation, extensions=[QueryDepthLimiter(max_depth=10)])
