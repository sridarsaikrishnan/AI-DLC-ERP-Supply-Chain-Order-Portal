"""Operator GraphQL schema. Requires the OPERATOR role; may expose ERP identity.

Admin mutations here are thin wrappers around already-built application services
(`ConnectionService`, `BindingService`, `QuoteService`, fulfillment services) — this
schema holds no new business logic.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import strawberry
from strawberry.extensions import QueryDepthLimiter

from src.modules.reference.connections.application.service import ConnectionService
from src.modules.reference.connections.domain.models import ErpConnection, ErpType
from src.modules.reference.tenancy.application.service import BindingService
from src.modules.sales.quoting.domain.models import EndCustomer, Quote, QuoteLine, Subsidiary
from src.shared.money import Money, TaxRate
from src.shared.types import BindingId, ConnectionId, TenantId

from .types import (
    BindingType,
    ConnectionType,
    MoneyType,
    OperatorOrder,
    OperatorOrderLineType,
    OperatorPartiesType,
    OperatorTimelineEntryType,
    OrderEventType,
    QuoteLineInput,
    QuoteLineType,
    QuoteType,
    SubsidiaryType,
)

if TYPE_CHECKING:
    from strawberry.types import Info

    from src.modules.reference.tenancy.domain.models import TenantConnectionBinding
    from src.modules.sales.ordering.projections.read_models import OperatorOrderView

    from ..context import GraphQLContext


def _money_to_gql(money: Money | None) -> MoneyType | None:
    return None if money is None else MoneyType(amount=str(money.amount), currency=money.currency)


def _order_to_gql(view: OperatorOrderView) -> OperatorOrder:
    return OperatorOrder(
        order_id=view.order_id,
        tenant_id=view.tenant_id,
        client_reference=view.client_reference,
        status=view.status,
        owning_connection_id=view.owning_connection_id,
        erp_order_id=view.erp_order_id,
        lines=[
            OperatorOrderLineType(
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
            OperatorTimelineEntryType(status=t.status, occurred_at=t.occurred_at)
            for t in view.timeline
        ],
        subtotal=_money_to_gql(view.subtotal),
        fulfillment_status=view.fulfillment_status,
        delivery_status=view.delivery_status,
        invoice_status=view.invoice_status,
        parties=OperatorPartiesType(
            end_customer_name=view.parties.end_customer_name,
            ship_to=view.parties.ship_to,
            subsidiary_id=view.parties.subsidiary_id,
            quote_id=view.parties.quote_id,
        ),
    )


def _connection_to_gql(connection: ErpConnection) -> ConnectionType:
    return ConnectionType(
        connection_id=str(connection.connection_id),
        erp_type=connection.erp_type.value,
        instance_label=connection.instance_label,
        base_url=connection.base_url,
        credentials=dict(connection.credentials),
        status=connection.status.value,
        secret_ref=connection.secret_ref,
        has_webhook_secret=connection.webhook_secret_ref is not None,
    )


def _binding_to_gql(binding: TenantConnectionBinding) -> BindingType:
    return BindingType(
        binding_id=str(binding.binding_id),
        tenant_id=str(binding.tenant_id),
        connection_id=str(binding.connection_id),
        erp_customer_id=binding.erp_customer_id,
        status=binding.status.value,
    )


def _company_to_gql(company: Subsidiary) -> SubsidiaryType:
    return SubsidiaryType(
        subsidiary_id=company.subsidiary_id,
        name=company.name,
        country=company.country,
        language=company.language,
    )


def _quote_to_gql(quote: Quote) -> QuoteType:
    return QuoteType(
        quote_id=quote.quote_id,
        tenant_id=str(quote.tenant_id),
        subsidiary_id=quote.subsidiary_id,
        end_customer_name=quote.end_customer.name,
        ship_to=quote.end_customer.ship_to,
        currency=quote.currency,
        valid_from=quote.valid_from.isoformat(),
        valid_until=quote.valid_until.isoformat(),
        status=quote.status.value,
        routed_to_connection_id=quote.routed_to_connection_id,
        lines=[
            QuoteLineType(
                product_key=line.product_key,
                name=line.name,
                kind=line.kind,
                unit_price=MoneyType(
                    amount=str(line.unit_price.amount), currency=line.unit_price.currency
                ),
                unit_of_measure=line.unit_of_measure,
                tax_code=line.tax_rate.code if line.tax_rate else None,
                tax_rate=float(line.tax_rate.rate) if line.tax_rate else None,
                line_discount=_money_to_gql(line.line_discount),
            )
            for line in quote.lines
        ],
    )


@strawberry.type
class Query:
    @strawberry.field
    def order(self, info: Info[GraphQLContext, None], order_id: str) -> OperatorOrder | None:
        ctx = info.context
        ctx.require_role("OPERATOR")
        view = ctx.container.projections.get_operator_view(order_id)
        return _order_to_gql(view) if view else None

    @strawberry.field
    def orders(self, info: Info[GraphQLContext, None]) -> list[OperatorOrder]:
        """Every order, across every tenant — operator debugging/visibility, never
        reseller-reachable (the reseller schema's `orders` stays tenant-scoped)."""
        ctx = info.context
        ctx.require_role("OPERATOR")
        return [_order_to_gql(v) for v in ctx.container.projections.list_operator_views()]

    @strawberry.field
    def order_events(self, info: Info[GraphQLContext, None], order_id: str) -> list[OrderEventType]:
        """The raw event stream for one order, in order — the event-sourcing/developer
        view. Reads `events` directly, not a projection."""
        ctx = info.context
        ctx.require_role("OPERATOR")
        events = ctx.container.event_store.load(order_id)
        return [
            OrderEventType(
                event_type=e.event_type,
                version=e.version,
                occurred_at=e.occurred_at.isoformat(),
                correlation_id=e.correlation_id,
                payload=dict(e.payload),
            )
            for e in events
        ]

    @strawberry.field
    def connections(self, info: Info[GraphQLContext, None]) -> list[ConnectionType]:
        ctx = info.context
        ctx.require_role("OPERATOR")
        return [_connection_to_gql(c) for c in ctx.container.connections.list_all()]

    @strawberry.field
    def bindings(self, info: Info[GraphQLContext, None]) -> list[BindingType]:
        ctx = info.context
        ctx.require_role("OPERATOR")
        return [_binding_to_gql(b) for b in ctx.container.bindings.list_all()]

    @strawberry.field
    def subsidiaries(self, info: Info[GraphQLContext, None]) -> list[SubsidiaryType]:
        ctx = info.context
        ctx.require_role("OPERATOR")
        return [_company_to_gql(c) for c in ctx.container.quote_service.list_subsidiaries()]

    @strawberry.field
    def erp_route(self, info: Info[GraphQLContext, None], subsidiary_id: str) -> str | None:
        """Which ERP connection this subsidiary's quotes currently route to — `None` until
        an operator sets one (Increment 7); `issueQuote` refuses until it's set."""
        ctx = info.context
        ctx.require_role("OPERATOR")
        return ctx.container.quote_service.get_erp_route(subsidiary_id)

    @strawberry.field
    def quotes(self, info: Info[GraphQLContext, None]) -> list[QuoteType]:
        ctx = info.context
        ctx.require_role("OPERATOR")
        return [_quote_to_gql(q) for q in ctx.container.quote_service.list_quotes()]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def register_connection(
        self,
        info: Info[GraphQLContext, None],
        erp_type: str,
        instance_label: str,
        base_url: str,
        credentials: strawberry.scalars.JSON,
        secret_ref: str,
        webhook_secret_ref: str | None = None,
    ) -> ConnectionType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = ConnectionService(ctx.container.connections, ctx.container.facts)
        connection = service.register(
            erp_type=ErpType(erp_type),
            instance_label=instance_label,
            base_url=base_url,
            credentials={str(k): str(v) for k, v in dict(credentials).items()},
            secret_ref=secret_ref,
            webhook_secret_ref=webhook_secret_ref,
        )
        return _connection_to_gql(connection)

    @strawberry.mutation
    def create_binding(
        self,
        info: Info[GraphQLContext, None],
        tenant_id: str,
        connection_id: str,
        erp_customer_id: str,
    ) -> BindingType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = BindingService(ctx.container.bindings, ctx.container.facts)
        binding = service.create_binding(
            tenant_id=TenantId(tenant_id),
            connection_id=ConnectionId(connection_id),
            erp_customer_id=erp_customer_id,
        )
        return _binding_to_gql(binding)

    @strawberry.mutation
    def verify_binding(self, info: Info[GraphQLContext, None], binding_id: str) -> BindingType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = BindingService(ctx.container.bindings, ctx.container.facts)
        binding = service.verify_binding(BindingId(binding_id))
        return _binding_to_gql(binding)

    @strawberry.mutation
    def pause_connection(
        self, info: Info[GraphQLContext, None], connection_id: str
    ) -> ConnectionType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = ConnectionService(ctx.container.connections, ctx.container.facts)
        return _connection_to_gql(service.pause(ConnectionId(connection_id)))

    @strawberry.mutation
    def resume_connection(
        self, info: Info[GraphQLContext, None], connection_id: str
    ) -> ConnectionType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = ConnectionService(ctx.container.connections, ctx.container.facts)
        return _connection_to_gql(service.resume(ConnectionId(connection_id)))

    @strawberry.mutation
    def remove_binding(self, info: Info[GraphQLContext, None], binding_id: str) -> BindingType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = BindingService(ctx.container.bindings, ctx.container.facts)
        return _binding_to_gql(service.remove_binding(BindingId(binding_id)))

    # --- subsidiary + quotes (FR-B / FR-C) ---
    @strawberry.mutation
    def create_subsidiary(
        self, info: Info[GraphQLContext, None], name: str, country: str, language: str
    ) -> SubsidiaryType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        company = ctx.container.quote_service.create_subsidiary(
            name=name, country=country, language=language
        )
        return _company_to_gql(company)

    @strawberry.mutation
    def set_erp_route(
        self, info: Info[GraphQLContext, None], subsidiary_id: str, connection_id: str
    ) -> SubsidiaryType:
        """Which ERP connection this subsidiary's quotes route to (Increment 7) — replaces
        whatever route it had before; quotes already issued keep the one they were
        stamped with."""
        ctx = info.context
        ctx.require_role("OPERATOR")
        ctx.container.quote_service.set_erp_route(subsidiary_id, connection_id)
        company = ctx.container.quote_service.get_subsidiary(subsidiary_id)
        assert company is not None
        return _company_to_gql(company)

    @strawberry.mutation
    def issue_quote(
        self,
        info: Info[GraphQLContext, None],
        tenant_id: str,
        subsidiary_id: str,
        end_customer_name: str,
        ship_to: str,
        currency: str,
        valid_from: str,
        valid_until: str,
        lines: list[QuoteLineInput],
    ) -> QuoteType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        quote_lines = [
            QuoteLine(
                product_key=li.product_key,
                name=li.name,
                kind=li.kind,
                unit_price=Money(Decimal(str(li.unit_price)), currency),
                unit_of_measure=li.unit_of_measure,
                tax_rate=(
                    TaxRate(
                        code=li.tax_code, rate=Decimal(str(li.tax_rate)), inclusive=li.tax_inclusive
                    )
                    if li.tax_code is not None and li.tax_rate is not None
                    else None
                ),
                line_discount=Money(Decimal(str(li.line_discount)), currency)
                if li.line_discount is not None
                else None,
            )
            for li in lines
        ]
        quote = ctx.container.quote_service.issue_quote(
            tenant_id=TenantId(tenant_id),
            subsidiary_id=subsidiary_id,
            end_customer=EndCustomer(name=end_customer_name, ship_to=ship_to),
            currency=currency,
            valid_from=date.fromisoformat(valid_from),
            valid_until=date.fromisoformat(valid_until),
            lines=quote_lines,
        )
        return _quote_to_gql(quote)

    @strawberry.mutation
    def set_vendor_date(
        self, info: Info[GraphQLContext, None], order_id: str, line_id: str, vendor_date: str
    ) -> bool:
        """Purchasing bought the line from the maker on `vendor_date` — "scheduled" (FR-E1).
        No Vendor Order document yet (FR-E2)."""
        ctx = info.context
        ctx.require_role("OPERATOR")
        order = ctx.container.orders.get(order_id)
        order.set_vendor_date(line_id, vendor_date)
        ctx.container.orders.save(order)
        ctx.container.drain()
        return True


def build_operator_schema() -> strawberry.Schema:
    return strawberry.Schema(
        query=Query, mutation=Mutation, extensions=[QueryDepthLimiter(max_depth=10)]
    )
