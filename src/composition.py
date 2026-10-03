"""Composition root — the one place the object graph is wired.

Bridges modules to each other's ports (ownership, bindings, connection resolution) and
selects infrastructure by `settings.profile`:
- "memory": in-memory bus + event store, for local dev/tests (no infra),
- "postgres": PostgresEventStore + Postgres repos/projection store + real/stub Odoo
  adapter + Secrets Manager. The repo publishes nothing itself (PostgresEventStore writes
  the outbox row in the same transaction as the event); the outbox relay and SQS consumers
  (worker, item C) do the async delivery. `order_processor` / `delivery_handler` /
  `order_projector` are exposed on the container so the worker can wire the same handler
  instances into `SqsConsumerRunner`s without re-deriving the object graph.

Kept out of the domain: this module is allowed to import everything; nothing imports it
except the api/worker hosts.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

log = logging.getLogger(__name__)

from src.modules.catalog.application.ports import ItemRepository
from src.modules.catalog.infrastructure.memory import InMemoryItemRepository
from src.modules.catalog.infrastructure.postgres import PostgresItemRepository
from src.modules.connections.application.ports import ConnectionRepository
from src.modules.connections.infrastructure.memory import InMemoryConnectionRepository
from src.modules.connections.infrastructure.postgres import PostgresConnectionRepository
from src.modules.fulfillment.application.service import (
    FulfillmentService,
    InvoiceService,
    PaymentService,
    ReturnService,
)
from src.modules.fulfillment.domain.aggregates import Fulfillment, Invoice, Payment, Return
from src.modules.integration.application.delivery import DeliveryHandler
from src.modules.integration.application.ports import ErpAdapter, ErpTarget, UnknownErpType
from src.modules.integration.application.reconcile import ReconcileSweeper
from src.modules.integration.infrastructure.registry import build_adapter_registry
from src.modules.integration.infrastructure.stub_adapter import StubErpAdapter
from src.modules.ordering.application.adapters import (
    OrderCommandAdapter,
    OrderReaderAdapter,
    StatusApplier,
)
from src.modules.ordering.application.order_service import OrderService
from src.modules.ordering.application.processing import OrderProcessor
from src.modules.ordering.domain.aggregate import Order
from src.modules.ordering.projections.postgres_store import PostgresOrderProjectionStore
from src.modules.ordering.projections.projector import OrderProjector
from src.modules.ordering.projections.store import OrderProjectionStore
from src.modules.quoting.application.ports import OperatingCompanyRepository, QuoteRepository
from src.modules.quoting.application.service import QuoteService
from src.modules.quoting.infrastructure.memory import (
    InMemoryOperatingCompanyRepository,
    InMemoryQuoteRepository,
)
from src.modules.quoting.infrastructure.postgres import (
    PostgresOperatingCompanyRepository,
    PostgresQuoteRepository,
)
from src.modules.tenancy.application.ports import BindingRepository
from src.modules.tenancy.infrastructure.memory import InMemoryBindingRepository
from src.modules.tenancy.infrastructure.postgres import PostgresBindingRepository
from src.modules.webhooks_inbound.application.ingress import InboundWebhookService
from src.modules.webhooks_inbound.infrastructure.memory import (
    InMemoryDedupStore,
    InMemoryOrderLocator,
)
from src.modules.webhooks_inbound.infrastructure.postgres import (
    PostgresDedupStore,
    PostgresOrderLocator,
)
from src.modules.webhooks_outbound.application.dispatch import WebhookDispatchService
from src.modules.webhooks_outbound.application.ports import (
    WebhookDeliveryRepository,
    WebhookEndpointRepository,
)
from src.modules.webhooks_outbound.domain.models import DISPATCHABLE_EVENT_TYPES
from src.modules.webhooks_outbound.infrastructure.http_sender import HttpWebhookSender
from src.modules.webhooks_outbound.infrastructure.memory import (
    InMemoryWebhookDeliveryRepository,
    InMemoryWebhookEndpointRepository,
)
from src.modules.webhooks_outbound.infrastructure.postgres import (
    PostgresWebhookDeliveryRepository,
    PostgresWebhookEndpointRepository,
)
from src.shared.config import Settings, get_settings
from src.shared.eventsourcing import EventSourcedRepository, EventStore, InMemoryEventStore
from src.shared.identity import (
    CognitoIdentityProvider,
    HeaderStubIdentityProvider,
    IdentityProvider,
)
from src.shared.identity.cognito import issuer_url
from src.shared.messaging import InMemoryMessageBus
from src.shared.messaging.facts import BusFactPublisher, FactPublisher, OutboxFactPublisher
from src.shared.persistence.engine import PostgresUnitOfWork, get_session_factory
from src.shared.persistence.event_store import PostgresEventStore
from src.shared.secrets import EnvSecretStore, SecretStore
from src.shared.secrets.aws import SecretsManagerSecretStore
from src.shared.types import ConnectionId, TenantId
from src.shared.unit_of_work import NullUnitOfWork


# --- bridge adapters: other modules' repos -> the ports ordering/integration expect ---
class CatalogOwnershipQuery:
    def __init__(self, items: ItemRepository) -> None:
        self._items = items

    def owner_of(self, product_key: str) -> ConnectionId | None:
        item = self._items.find_by_sku(product_key)
        return item.owning_connection_id if item else None


class TenancyBindingQuery:
    def __init__(self, bindings: BindingRepository) -> None:
        self._bindings = bindings

    def is_bound(self, tenant_id: TenantId, connection_id: ConnectionId) -> bool:
        binding = self._bindings.find_by_tenant_and_connection(tenant_id, connection_id)
        return binding is not None and binding.is_verified


class TenancyCustomerDirectory:
    """Resolves a reseller's ERP customer id for a connection, from the binding — the id
    the order is sent to the ERP as (FR-A1). Operator-only data; stays off reseller views."""

    def __init__(self, bindings: BindingRepository) -> None:
        self._bindings = bindings

    def erp_customer_id_for(self, tenant_id: TenantId, connection_id: ConnectionId) -> str | None:
        binding = self._bindings.find_by_tenant_and_connection(tenant_id, connection_id)
        return binding.erp_customer_id if binding is not None else None


class ConnectionsResolver:
    def __init__(self, connections: ConnectionRepository, secrets: SecretStore) -> None:
        self._connections = connections
        self._secrets = secrets

    def resolve(self, connection_id: ConnectionId) -> ErpTarget | None:
        connection = self._connections.get(connection_id)
        if connection is None or not connection.is_active:
            return None
        return ErpTarget(
            erp_type=connection.erp_type.value,
            base_url=connection.base_url,
            credentials=dict(connection.credentials),
            secret=self._secrets.get_secret(connection.secret_ref),
        )


class ConnectionWebhookSecretResolver:
    """Resolves the per-connection inbound-webhook secret — `webhook_secret_ref`, which
    is deliberately NOT the same secret as the ERP login credential (`secret_ref`); see
    `ErpConnection.webhook_secret_ref`. `None` (no secret configured, or resolution
    failed) means this connection hasn't onboarded webhooks yet — every webhook for it
    is rejected UNAUTHORIZED, which is correct: it falls back to the reconcile sweeper."""

    def __init__(self, connections: ConnectionRepository, secrets: SecretStore) -> None:
        self._connections = connections
        self._secrets = secrets

    def secret_for(self, connection_id: ConnectionId) -> str | None:
        connection = self._connections.get(connection_id)
        if connection is None or connection.webhook_secret_ref is None:
            return None
        try:
            return self._secrets.get_secret(connection.webhook_secret_ref)
        except Exception:
            return None


@dataclass
class Container:
    settings: Settings
    order_service: OrderService
    projections: OrderProjectionStore | PostgresOrderProjectionStore
    ingress: InboundWebhookService
    bus: InMemoryMessageBus | None  # None in the postgres profile (no synchronous bus)
    drain: Callable[[], None]  # memory: bus.run_until_empty; postgres: no-op, worker drains
    connections: ConnectionRepository
    items: ItemRepository
    bindings: BindingRepository
    order_processor: OrderProcessor
    delivery_handler: DeliveryHandler
    order_projector: OrderProjector
    reconcile_sweeper: ReconcileSweeper | None  # None in the memory profile (worker-only)
    identity: IdentityProvider
    event_store: EventStore  # raw event access — the operator "order events" dev view reads this directly
    webhook_endpoints: WebhookEndpointRepository
    webhook_deliveries: WebhookDeliveryRepository
    webhook_dispatcher: WebhookDispatchService
    secrets: SecretStore  # exposed so WebhookEndpointService (GraphQL layer) can generate+store signing secrets
    facts: FactPublisher  # catalog/connections/tenancy publish notifications through this, see src/shared/messaging/facts.py
    fulfillment_service: FulfillmentService
    invoice_service: InvoiceService
    payment_service: PaymentService
    return_service: ReturnService
    orders: EventSourcedRepository[Order]  # exposed so GraphQL can read fulfillment_status/invoice_status (derived, aggregate-only)
    quote_service: QuoteService
    quotes: QuoteRepository
    operating_companies: OperatingCompanyRepository


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    if settings.profile == "postgres":
        return _build_postgres_container(settings)
    return _build_memory_container(settings)


def _build_memory_container(settings: Settings) -> Container:
    event_store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(event_store, Order, publisher=bus)
    # Same event store as Order — one `events` table in Postgres too, differentiated by
    # aggregate_type + stream_id, not a separate store per aggregate type.
    uow = NullUnitOfWork()  # memory can't partially fail across appends (FR-A4 is a no-op here)
    fulfillment_service = FulfillmentService(EventSourcedRepository(event_store, Fulfillment), repo, uow)
    invoice_service = InvoiceService(EventSourcedRepository(event_store, Invoice), repo, uow)
    payment_service = PaymentService(EventSourcedRepository(event_store, Payment))
    return_service = ReturnService(EventSourcedRepository(event_store, Return))

    connections = InMemoryConnectionRepository()
    items = InMemoryItemRepository()
    bindings = InMemoryBindingRepository()
    quotes = InMemoryQuoteRepository()
    operating_companies = InMemoryOperatingCompanyRepository()
    quote_service = QuoteService(quotes, operating_companies)
    secrets: SecretStore = EnvSecretStore()

    projections = OrderProjectionStore()
    locator = InMemoryOrderLocator()

    erp_adapter: ErpAdapter = StubErpAdapter()
    adapter_for = lambda _erp_type: erp_adapter

    processor = OrderProcessor(repo, CatalogOwnershipQuery(items), TenancyBindingQuery(bindings))
    delivery = DeliveryHandler(
        connections=ConnectionsResolver(connections, secrets),
        orders_read=OrderReaderAdapter(projections, TenancyCustomerDirectory(bindings)),
        orders_cmd=OrderCommandAdapter(repo),
        adapter_for=adapter_for,
    )
    projector = OrderProjector(projections, locator=locator)

    webhook_endpoints = InMemoryWebhookEndpointRepository()
    webhook_deliveries = InMemoryWebhookDeliveryRepository()
    webhook_dispatcher = WebhookDispatchService(
        endpoints=webhook_endpoints,
        deliveries=webhook_deliveries,
        secrets=secrets,
        sender=HttpWebhookSender(),
        orders=projections,
    )

    bus.subscribe("projections", projector.handle)
    bus.subscribe("order-processing", processor.handle, event_types={"OrderSubmitted"})
    bus.subscribe("order-delivery", delivery.handle, event_types={"OrderReadyForDelivery"})
    bus.subscribe("webhook-dispatch", webhook_dispatcher.handle, event_types=set(DISPATCHABLE_EVENT_TYPES))

    ingress = InboundWebhookService(
        secrets=ConnectionWebhookSecretResolver(connections, secrets),
        dedup=InMemoryDedupStore(),
        locator=locator,
        order_status=StatusApplier(repo),
    )

    return Container(
        settings=settings,
        order_service=OrderService(repo, quotes, items, quote_service),
        projections=projections,
        ingress=ingress,
        bus=bus,
        drain=bus.run_until_empty,
        connections=connections,
        items=items,
        bindings=bindings,
        order_processor=processor,
        delivery_handler=delivery,
        order_projector=projector,
        reconcile_sweeper=None,
        identity=HeaderStubIdentityProvider(),
        event_store=event_store,
        webhook_endpoints=webhook_endpoints,
        webhook_deliveries=webhook_deliveries,
        webhook_dispatcher=webhook_dispatcher,
        secrets=secrets,
        facts=BusFactPublisher(bus),
        fulfillment_service=fulfillment_service,
        invoice_service=invoice_service,
        payment_service=payment_service,
        return_service=return_service,
        orders=repo,
        quote_service=quote_service,
        quotes=quotes,
        operating_companies=operating_companies,
    )


def _resolve_adapter_for(settings: Settings) -> Callable[[str], ErpAdapter]:
    """`erp_adapter_mode="stub"` overrides every ERP type with the deterministic stub
    (local dev/testing, no real HTTP). Otherwise dispatch through the adapter registry —
    see `integration/infrastructure/registry.py` for how a new ERP gets added here."""
    if settings.erp_adapter_mode == "stub":
        stub = StubErpAdapter()
        return lambda _erp_type: stub

    registry = build_adapter_registry(settings)

    def resolve(erp_type: str) -> ErpAdapter:
        adapter = registry.get(erp_type)
        if adapter is None:
            raise UnknownErpType(erp_type)
        return adapter

    return resolve


def _resolve_identity_provider(settings: Settings) -> IdentityProvider:
    """Real Cognito verification once `COGNITO_USER_POOL_ID`/`COGNITO_CLIENT_ID` are
    configured; the header stub until then (so the postgres profile stays usable for
    local dev against floci — with a *live* Odoo/worker/SQS pipeline but no Cognito user
    pool set up yet — without hard-failing container construction). Set both env vars to
    turn on real verification; nothing else changes."""
    if not settings.cognito_user_pool_id or not settings.cognito_client_id:
        log.warning("COGNITO_USER_POOL_ID/COGNITO_CLIENT_ID not set — using the header stub, not real auth")
        return HeaderStubIdentityProvider()
    issuer = issuer_url(
        aws_endpoint_url=settings.aws_endpoint_url,
        aws_region=settings.aws_region,
        user_pool_id=settings.cognito_user_pool_id,
    )
    return CognitoIdentityProvider(
        user_pool_id=settings.cognito_user_pool_id,
        client_id=settings.cognito_client_id,
        issuer=issuer,
        resource_server_id=settings.cognito_resource_server_id,
    )


def _build_postgres_container(settings: Settings) -> Container:
    session_factory = get_session_factory(settings.database_url)
    event_store = PostgresEventStore(session_factory)
    # PostgresEventStore.append writes the outbox row in the same transaction as the
    # event — the repo must not also publish synchronously, or events would be delivered
    # twice (once here, once by the relay). outbox=None, publisher=None is deliberate.
    repo: EventSourcedRepository[Order] = EventSourcedRepository(event_store, Order)
    # Same reasoning as the memory profile: one `events` table, one store, differentiated
    # by aggregate_type + stream_id — these 4 aren't a separate Postgres setup.
    # One UoW so a fulfillment/invoice + its order quantity update commit together (FR-A4).
    uow = PostgresUnitOfWork(session_factory)
    fulfillment_service = FulfillmentService(EventSourcedRepository(event_store, Fulfillment), repo, uow)
    invoice_service = InvoiceService(EventSourcedRepository(event_store, Invoice), repo, uow)
    payment_service = PaymentService(EventSourcedRepository(event_store, Payment))
    return_service = ReturnService(EventSourcedRepository(event_store, Return))

    connections = PostgresConnectionRepository(session_factory)
    items = PostgresItemRepository(session_factory)
    bindings = PostgresBindingRepository(session_factory)
    quotes = PostgresQuoteRepository(session_factory)
    operating_companies = PostgresOperatingCompanyRepository(session_factory)
    quote_service = QuoteService(quotes, operating_companies)
    secrets: SecretStore = SecretsManagerSecretStore(
        endpoint_url=settings.aws_endpoint_url, region_name=settings.aws_region
    )
    identity = _resolve_identity_provider(settings)

    projections = PostgresOrderProjectionStore(session_factory)
    locator = PostgresOrderLocator(session_factory)

    adapter_for = _resolve_adapter_for(settings)

    connections_resolver = ConnectionsResolver(connections, secrets)
    status_applier = StatusApplier(repo)

    processor = OrderProcessor(repo, CatalogOwnershipQuery(items), TenancyBindingQuery(bindings))
    delivery = DeliveryHandler(
        connections=connections_resolver,
        orders_read=OrderReaderAdapter(projections, TenancyCustomerDirectory(bindings)),
        orders_cmd=OrderCommandAdapter(repo),
        adapter_for=adapter_for,
    )
    projector = OrderProjector(projections, locator=locator)

    ingress = InboundWebhookService(
        secrets=ConnectionWebhookSecretResolver(connections, secrets),
        dedup=PostgresDedupStore(session_factory),
        locator=locator,
        order_status=status_applier,
    )

    reconcile_sweeper = ReconcileSweeper(
        connections=connections_resolver,
        adapter_for=adapter_for,
        locator=locator,
        order_status=status_applier,
    )

    webhook_endpoints = PostgresWebhookEndpointRepository(session_factory)
    webhook_deliveries = PostgresWebhookDeliveryRepository(session_factory)
    webhook_dispatcher = WebhookDispatchService(
        endpoints=webhook_endpoints,
        deliveries=webhook_deliveries,
        secrets=secrets,
        sender=HttpWebhookSender(),
        orders=projections,
    )

    return Container(
        settings=settings,
        order_service=OrderService(repo, quotes, items, quote_service),
        projections=projections,
        ingress=ingress,
        bus=None,
        drain=lambda: None,
        connections=connections,
        items=items,
        bindings=bindings,
        order_processor=processor,
        delivery_handler=delivery,
        order_projector=projector,
        reconcile_sweeper=reconcile_sweeper,
        identity=identity,
        event_store=event_store,
        webhook_endpoints=webhook_endpoints,
        webhook_deliveries=webhook_deliveries,
        webhook_dispatcher=webhook_dispatcher,
        secrets=secrets,
        facts=OutboxFactPublisher(session_factory),
        fulfillment_service=fulfillment_service,
        invoice_service=invoice_service,
        payment_service=payment_service,
        return_service=return_service,
        orders=repo,
        quote_service=quote_service,
        quotes=quotes,
        operating_companies=operating_companies,
    )
