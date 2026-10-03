"""End-to-end, in-memory: the whole pipeline wired with real components.

place order -> (bus) order-processing routes by ownership -> order-delivery submits to a
stub ERP -> projections build the reseller read model + reverse-routing locator ->
inbound ERP webhook (status change) is authenticated + attributed + applied -> the
reseller read model reflects the new lifecycle status.

Everything below is production code except the ERP adapter (stub), the connection
resolver, and the ownership/binding queries (fakes standing in for the catalog/tenancy
adapters). The message bus, event store, repository, projector, processor, delivery
handler, status applier and webhook ingress are the real implementations.
"""

from __future__ import annotations

from src.modules.catalog.infrastructure.memory import InMemoryItemRepository
from src.modules.integration.application.delivery import DeliveryHandler
from src.modules.integration.application.ports import ErpTarget
from src.modules.integration.infrastructure.stub_adapter import StubErpAdapter
from src.modules.ordering.application.adapters import (
    OrderCommandAdapter,
    OrderReaderAdapter,
    StatusApplier,
)
from src.modules.ordering.application.order_service import OrderService
from src.modules.ordering.application.processing import OrderProcessor
from src.modules.ordering.domain.aggregate import Order
from src.modules.ordering.domain.models import OrderLine
from src.modules.ordering.projections.projector import OrderProjector
from src.modules.ordering.projections.store import OrderProjectionStore
from src.modules.webhooks_inbound.application.ingress import (
    InboundWebhook,
    InboundWebhookService,
    IngressOutcome,
)
from src.modules.webhooks_inbound.domain.signature import compute_signature
from src.modules.webhooks_inbound.infrastructure.memory import (
    InMemoryDedupStore,
    InMemoryOrderLocator,
)
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.messaging import InMemoryMessageBus
from src.shared.types import ConnectionId, TenantId

_TENANT = TenantId("tnt_demo")
_CONN = "conn_odoo_local"
_SECRET = "whsec_demo"


class FakeOwnership:
    def owner_of(self, product_key: str) -> ConnectionId | None:
        return ConnectionId(_CONN) if product_key in {"ANVIL", "SPRING"} else None


class FakeBindings:
    def is_bound(self, tenant_id: TenantId, connection_id: ConnectionId) -> bool:
        return str(tenant_id) == _TENANT and str(connection_id) == _CONN


class FakeConnections:
    def resolve(self, connection_id: ConnectionId) -> ErpTarget | None:
        if str(connection_id) != _CONN:
            return None
        return ErpTarget(erp_type="ODOO", base_url="http://odoo", database="odoo", username="admin", secret="x")


class FakeSecrets:
    def secret_for(self, connection_id: ConnectionId) -> str | None:
        return _SECRET if str(connection_id) == _CONN else None


def test_order_flows_place_to_confirmed_via_webhook() -> None:
    # --- shared infra ---
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    projections = OrderProjectionStore()
    locator = InMemoryOrderLocator()
    stub_adapter = StubErpAdapter()

    # --- consumers wired to the bus (real components) ---
    processor = OrderProcessor(repo, FakeOwnership(), FakeBindings())
    delivery = DeliveryHandler(
        connections=FakeConnections(),
        orders_read=OrderReaderAdapter(projections),
        orders_cmd=OrderCommandAdapter(repo),
        adapter_for=lambda _erp_type: stub_adapter,
    )
    bus.subscribe("projections", OrderProjector(projections, locator=locator).handle)
    bus.subscribe("order-processing", processor.handle, event_types={"OrderSubmitted"})
    bus.subscribe("order-delivery", delivery.handle, event_types={"OrderReadyForDelivery"})

    # --- place an order and drain the pipeline ---
    order_id = OrderService(repo, InMemoryItemRepository()).place_order(
        tenant_id=_TENANT,
        client_reference="PO-1001",
        lines=[OrderLine(product_key="ANVIL", quantity=3, unit_of_measure="EA")],
    )
    bus.run_until_empty()

    # routed, delivered to the (stub) ERP, projection reflects it, no ERP identity leaked
    reseller = projections.get_reseller_view(_TENANT, order_id)
    assert reseller is not None and reseller.status == "Sent to ERP"
    operator = projections.get_operator_view(order_id)
    assert operator is not None and operator.owning_connection_id == _CONN
    erp_order_id = operator.erp_order_id
    assert erp_order_id is not None  # locator now knows (conn, erp_order_id) -> order

    # --- inbound ERP webhook: the order was confirmed in Odoo ---
    ingress = InboundWebhookService(
        secrets=FakeSecrets(),
        dedup=InMemoryDedupStore(),
        locator=locator,
        order_status=StatusApplier(repo),
    )
    body = b'{"state":"sale"}'
    outcome = ingress.handle(
        InboundWebhook(
            connection_id=ConnectionId(_CONN),
            erp_type="ODOO",
            erp_order_id=erp_order_id,
            native_status="sale",
            event_ref="evt-1",
            raw_body=body,
            signature=compute_signature(_SECRET, body),
        )
    )
    bus.run_until_empty()  # StatusApplier saved -> OrderConfirmed -> projector updates read model

    assert outcome is IngressOutcome.ACCEPTED
    reseller_after = projections.get_reseller_view(_TENANT, order_id)
    assert reseller_after is not None and reseller_after.status == "Confirmed"
    # reseller view still carries no ERP identity
    assert not hasattr(reseller_after, "erp_order_id")
