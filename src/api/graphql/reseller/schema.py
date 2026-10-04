"""Reseller GraphQL schema: queries over projections, mutations mapped to commands.

Depth/complexity limits are applied; introspection is disabled in production (api/app.py).
Every resolver is tenant-scoped via the context.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import strawberry
from strawberry.extensions import QueryDepthLimiter

from src.modules.integration.webhooks_outbound.application.service import WebhookEndpointService
from src.modules.sales.ordering.application.order_service import OrderLineInput as OrderLineCommand
from src.modules.sales.ordering.domain.errors import DuplicateOrderReference
from src.modules.sales.quoting.domain.errors import PriceNotQuoted, QuoteNotFound, QuoteNotValid
from src.shared.types import OrderId, TenantId, WebhookEndpointId

from .types import (
    MoneyType,
    OrderLineInput,
    OrderLineType,
    PartiesType,
    QuoteLineType,
    QuoteType,
    ResellerOrder,
    TimelineEntryType,
    WebhookDeliveryType,
    WebhookEndpointCreatedType,
    WebhookEndpointType,
)

if TYPE_CHECKING:
    from strawberry.types import Info

    from src.modules.integration.webhooks_outbound.domain.models import (
        WebhookDelivery,
        WebhookEndpoint,
    )
    from src.modules.sales.ordering.projections.read_models import ResellerOrderView
    from src.modules.sales.quoting.domain.models import Quote
    from src.shared.money import Money

    from ..context import GraphQLContext


def _money_to_gql(money: Money | None) -> MoneyType | None:
    return None if money is None else MoneyType(amount=str(money.amount), currency=money.currency)


def _to_gql(view: ResellerOrderView) -> ResellerOrder:
    return ResellerOrder(
        order_id=view.order_id,
        client_reference=view.client_reference,
        status=view.status,
        lines=[
            OrderLineType(
                product_key=line.product_key,
                quantity=line.quantity,
                unit_of_measure=line.unit_of_measure,
                line_id=line.line_id,
                kind=line.kind,
                unit_price=_money_to_gql(line.unit_price),
                line_total=_money_to_gql(line.line_total),
                shipped_quantity=line.shipped_quantity,
                delivered_quantity=line.delivered_quantity,
                invoiced_quantity=line.invoiced_quantity,
                scheduled_date=line.scheduled_date,
            )
            for line in view.lines
        ],
        timeline=[
            TimelineEntryType(status=t.status, occurred_at=t.occurred_at) for t in view.timeline
        ],
        subtotal=_money_to_gql(view.subtotal),
        fulfillment_status=view.fulfillment_status,
        delivery_status=view.delivery_status,
        invoice_status=view.invoice_status,
        parties=PartiesType(
            end_customer_name=view.parties.end_customer_name,
            ship_to=view.parties.ship_to,
            operating_company_id=view.parties.operating_company_id,
            quote_id=view.parties.quote_id,
        ),
    )


def _quote_to_gql(quote: Quote) -> QuoteType:
    return QuoteType(
        quote_id=quote.quote_id,
        operating_company_id=quote.operating_company_id,
        end_customer_name=quote.end_customer.name,
        ship_to=quote.end_customer.ship_to,
        currency=quote.currency,
        valid_from=quote.valid_from.isoformat(),
        valid_until=quote.valid_until.isoformat(),
        status=quote.status.value,
        lines=[
            QuoteLineType(
                product_key=line.product_key,
                unit_price=MoneyType(
                    amount=str(line.unit_price.amount), currency=line.unit_price.currency
                ),
                unit_of_measure=line.unit_of_measure,
            )
            for line in quote.lines
        ],
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
    def quotes(self, info: Info[GraphQLContext, None]) -> list[QuoteType]:
        """Quotes issued to this reseller — what you can place an order against."""
        ctx = info.context
        return [
            _quote_to_gql(q)
            for q in ctx.container.quote_service.list_quotes_for_tenant(TenantId(ctx.tenant_id))
        ]

    @strawberry.field
    def quote(self, info: Info[GraphQLContext, None], quote_id: str) -> QuoteType | None:
        ctx = info.context
        quote = ctx.container.quote_service.get_quote(quote_id)
        if (
            quote is None or str(quote.tenant_id) != ctx.tenant_id
        ):  # tenant scoping (FR-19 / fail-closed)
            return None
        return _quote_to_gql(quote)

    @strawberry.field
    def webhook_endpoints(self, info: Info[GraphQLContext, None]) -> list[WebhookEndpointType]:
        ctx = info.context
        return [
            _endpoint_to_gql(e)
            for e in ctx.container.webhook_endpoints.list_by_tenant(TenantId(ctx.tenant_id))
        ]

    @strawberry.field
    def delivery_log(self, info: Info[GraphQLContext, None]) -> list[WebhookDeliveryType]:
        """Every webhook delivery attempt for this tenant — what got sent to your
        endpoints, and whether it arrived."""
        ctx = info.context
        return [
            _delivery_to_gql(d)
            for d in ctx.container.webhook_deliveries.list_by_tenant(TenantId(ctx.tenant_id))
        ]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def place_order(
        self,
        info: Info[GraphQLContext, None],
        quote_id: str,
        client_reference: str,
        lines: list[OrderLineInput],
    ) -> str:
        """Place an order as a reply to a quote (FR-B2). Price comes from the quote; a line
        with no quoted price, or a missing/expired quote, is refused (FR-B3)."""
        ctx = info.context
        try:
            order_id = ctx.container.order_service.place_order(
                tenant_id=TenantId(ctx.tenant_id),
                quote_id=quote_id,
                client_reference=client_reference,
                lines=[OrderLineCommand(li.product_key, Decimal(str(li.quantity))) for li in lines],
            )
        except (QuoteNotFound, QuoteNotValid) as exc:
            raise ValueError(f"quote unavailable: {exc}") from exc
        except PriceNotQuoted as exc:
            raise ValueError(str(exc)) from exc
        except DuplicateOrderReference as exc:
            raise ValueError(str(exc)) from exc
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
        self,
        info: Info[GraphQLContext, None],
        name: str,
        url: str,
        event_types: list[str] | None = None,
    ) -> WebhookEndpointCreatedType:
        ctx = info.context
        service = WebhookEndpointService(ctx.container.webhook_endpoints, ctx.container.secrets)
        endpoint, raw_secret = service.register(
            tenant_id=TenantId(ctx.tenant_id),
            name=name,
            url=url,
            event_types=frozenset(event_types) if event_types else None,
        )
        return WebhookEndpointCreatedType(
            endpoint=_endpoint_to_gql(endpoint), signing_secret=raw_secret
        )

    @strawberry.mutation
    def pause_webhook_endpoint(
        self, info: Info[GraphQLContext, None], endpoint_id: str
    ) -> WebhookEndpointType:
        ctx = info.context
        service = WebhookEndpointService(ctx.container.webhook_endpoints, ctx.container.secrets)
        return _endpoint_to_gql(
            service.pause(WebhookEndpointId(endpoint_id), tenant_id=TenantId(ctx.tenant_id))
        )

    @strawberry.mutation
    def resume_webhook_endpoint(
        self, info: Info[GraphQLContext, None], endpoint_id: str
    ) -> WebhookEndpointType:
        ctx = info.context
        service = WebhookEndpointService(ctx.container.webhook_endpoints, ctx.container.secrets)
        return _endpoint_to_gql(
            service.resume(WebhookEndpointId(endpoint_id), tenant_id=TenantId(ctx.tenant_id))
        )


def build_reseller_schema() -> strawberry.Schema:
    return strawberry.Schema(
        query=Query, mutation=Mutation, extensions=[QueryDepthLimiter(max_depth=10)]
    )
