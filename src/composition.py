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

from collections.abc import Callable
from dataclasses import dataclass

from src.modules.catalog.application.ports import ItemRepository
from src.modules.catalog.infrastructure.memory import InMemoryItemRepository
from src.modules.catalog.infrastructure.postgres import PostgresItemRepository
from src.modules.connections.application.ports import ConnectionRepository
from src.modules.connections.infrastructure.memory import InMemoryConnectionRepository
from src.modules.connections.infrastructure.postgres import PostgresConnectionRepository
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
from src.shared.config import Settings, get_settings
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.messaging import InMemoryMessageBus
from src.shared.persistence.engine import get_session_factory
from src.shared.persistence.event_store import PostgresEventStore
from src.shared.secrets import EnvSecretStore, SecretsManagerSecretStore, SecretStore
from src.shared.types import ConnectionId, TenantId


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
            database=connection.database,
            username=connection.username,
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
        except Exception:  # noqa: BLE001
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


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    if settings.profile == "postgres":
        return _build_postgres_container(settings)
    return _build_memory_container(settings)


def _build_memory_container(settings: Settings) -> Container:
    event_store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(event_store, Order, publisher=bus)

    connections = InMemoryConnectionRepository()
    items = InMemoryItemRepository()
    bindings = InMemoryBindingRepository()
    secrets: SecretStore = EnvSecretStore()

    projections = OrderProjectionStore()
    locator = InMemoryOrderLocator()

    erp_adapter: ErpAdapter = StubErpAdapter()
    adapter_for = lambda _erp_type: erp_adapter  # noqa: E731

    processor = OrderProcessor(repo, CatalogOwnershipQuery(items), TenancyBindingQuery(bindings))
    delivery = DeliveryHandler(
        connections=ConnectionsResolver(connections, secrets),
        orders_read=OrderReaderAdapter(projections),
        orders_cmd=OrderCommandAdapter(repo),
        adapter_for=adapter_for,
    )
    projector = OrderProjector(projections, locator=locator)

    bus.subscribe("projections", projector.handle)
    bus.subscribe("order-processing", processor.handle, event_types={"OrderSubmitted"})
    bus.subscribe("order-delivery", delivery.handle, event_types={"OrderReadyForDelivery"})

    ingress = InboundWebhookService(
        secrets=ConnectionWebhookSecretResolver(connections, secrets),
        dedup=InMemoryDedupStore(),
        locator=locator,
        order_status=StatusApplier(repo),
    )

    return Container(
        settings=settings,
        order_service=OrderService(repo),
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


def _build_postgres_container(settings: Settings) -> Container:
    session_factory = get_session_factory(settings.database_url)
    event_store = PostgresEventStore(session_factory)
    # PostgresEventStore.append writes the outbox row in the same transaction as the
    # event — the repo must not also publish synchronously, or events would be delivered
    # twice (once here, once by the relay). outbox=None, publisher=None is deliberate.
    repo: EventSourcedRepository[Order] = EventSourcedRepository(event_store, Order)

    connections = PostgresConnectionRepository(session_factory)
    items = PostgresItemRepository(session_factory)
    bindings = PostgresBindingRepository(session_factory)
    secrets: SecretStore = SecretsManagerSecretStore(
        endpoint_url=settings.aws_endpoint_url, region_name=settings.aws_region
    )

    projections = PostgresOrderProjectionStore(session_factory)
    locator = PostgresOrderLocator(session_factory)

    adapter_for = _resolve_adapter_for(settings)

    connections_resolver = ConnectionsResolver(connections, secrets)
    status_applier = StatusApplier(repo)

    processor = OrderProcessor(repo, CatalogOwnershipQuery(items), TenancyBindingQuery(bindings))
    delivery = DeliveryHandler(
        connections=connections_resolver,
        orders_read=OrderReaderAdapter(projections),
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

    return Container(
        settings=settings,
        order_service=OrderService(repo),
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
    )
