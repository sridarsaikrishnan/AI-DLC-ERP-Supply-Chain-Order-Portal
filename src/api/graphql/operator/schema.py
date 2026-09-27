"""Operator GraphQL schema. Requires the OPERATOR role; may expose ERP identity.

Admin mutations here are thin wrappers around already-built, already-tested application
services (`ConnectionService`, `BindingService`, `CatalogService`) — this schema doesn't
contain any new business logic, it's the first GraphQL surface for logic that previously
only had a Python-script/raw-SQL entry point (`scripts/seed_demo.py`).
"""

from __future__ import annotations

import strawberry
from strawberry.extensions import QueryDepthLimiter
from strawberry.types import Info

from src.modules.catalog.application.service import CatalogService
from src.modules.catalog.domain.models import Item
from src.modules.connections.application.service import ConnectionService
from src.modules.connections.domain.models import ErpConnection, ErpType
from src.modules.ordering.projections.read_models import OperatorOrderView
from src.modules.tenancy.application.service import BindingService
from src.modules.tenancy.domain.models import TenantConnectionBinding
from src.shared.types import BindingId, ConnectionId, TenantId

from ..context import GraphQLContext
from .types import (
    BindingType,
    ConnectionType,
    ItemType,
    OperatorOrder,
    OperatorOrderLineType,
    OperatorTimelineEntryType,
    OrderEventType,
)

def _order_to_gql(view: OperatorOrderView) -> OperatorOrder:
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
        timeline=[OperatorTimelineEntryType(status=t.status, occurred_at=t.occurred_at) for t in view.timeline],
    )


def _connection_to_gql(connection: ErpConnection) -> ConnectionType:
    return ConnectionType(
        connection_id=str(connection.connection_id),
        erp_type=connection.erp_type.value,
        instance_label=connection.instance_label,
        base_url=connection.base_url,
        database=connection.database,
        username=connection.username,
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


def _item_to_gql(item: Item) -> ItemType:
    return ItemType(
        item_id=str(item.item_id), sku=item.sku, name=item.name, owning_connection_id=str(item.owning_connection_id)
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
        view. Reads `events` directly, not a projection: this is what actually happened,
        not a read model derived from it."""
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
        # list_all, not list_active: a paused connection must stay visible so it can be
        # resumed — list_active is for routing decisions (DeliveryHandler), not this UI.
        return [_connection_to_gql(c) for c in ctx.container.connections.list_all()]

    @strawberry.field
    def bindings(self, info: Info[GraphQLContext, None]) -> list[BindingType]:
        ctx = info.context
        ctx.require_role("OPERATOR")
        return [_binding_to_gql(b) for b in ctx.container.bindings.list_all()]

    @strawberry.field
    def items(self, info: Info[GraphQLContext, None]) -> list[ItemType]:
        ctx = info.context
        ctx.require_role("OPERATOR")
        return [_item_to_gql(i) for i in ctx.container.items.list_all()]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def register_connection(
        self,
        info: Info[GraphQLContext, None],
        erp_type: str,
        instance_label: str,
        base_url: str,
        database: str,
        username: str,
        secret_ref: str,
        webhook_secret_ref: str | None = None,
    ) -> ConnectionType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = ConnectionService(ctx.container.connections)
        connection = service.register(
            erp_type=ErpType(erp_type),  # unregistered ERP type -> ValueError -> a clean GraphQL error
            instance_label=instance_label,
            base_url=base_url,
            database=database,
            username=username,
            secret_ref=secret_ref,
            webhook_secret_ref=webhook_secret_ref,
        )
        return _connection_to_gql(connection)

    @strawberry.mutation
    def create_binding(
        self, info: Info[GraphQLContext, None], tenant_id: str, connection_id: str, erp_customer_id: str
    ) -> BindingType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = BindingService(ctx.container.bindings)
        binding = service.create_binding(
            tenant_id=TenantId(tenant_id), connection_id=ConnectionId(connection_id), erp_customer_id=erp_customer_id
        )
        return _binding_to_gql(binding)

    @strawberry.mutation
    def verify_binding(self, info: Info[GraphQLContext, None], binding_id: str) -> BindingType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = BindingService(ctx.container.bindings)
        binding = service.verify_binding(BindingId(binding_id))
        return _binding_to_gql(binding)

    @strawberry.mutation
    def sync_item(
        self, info: Info[GraphQLContext, None], sku: str, name: str, owning_connection_id: str
    ) -> ItemType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = CatalogService(ctx.container.items)
        item = service.sync_item(sku=sku, name=name, owning_connection_id=ConnectionId(owning_connection_id))
        return _item_to_gql(item)

    @strawberry.mutation
    def pause_connection(self, info: Info[GraphQLContext, None], connection_id: str) -> ConnectionType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = ConnectionService(ctx.container.connections)
        return _connection_to_gql(service.pause(ConnectionId(connection_id)))

    @strawberry.mutation
    def resume_connection(self, info: Info[GraphQLContext, None], connection_id: str) -> ConnectionType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = ConnectionService(ctx.container.connections)
        return _connection_to_gql(service.resume(ConnectionId(connection_id)))

    @strawberry.mutation
    def remove_binding(self, info: Info[GraphQLContext, None], binding_id: str) -> BindingType:
        ctx = info.context
        ctx.require_role("OPERATOR")
        service = BindingService(ctx.container.bindings)
        return _binding_to_gql(service.remove_binding(BindingId(binding_id)))


def build_operator_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, mutation=Mutation, extensions=[QueryDepthLimiter(max_depth=10)])
