"""An order already in the ERP is adopted, then an inbound webhook confirms it."""

from __future__ import annotations

from src.modules.integration.erp.application.ports import ErpPartnerOrderLine
from src.modules.integration.webhooks_inbound.application.ingress import (
    InboundWebhook,
    InboundWebhookService,
    IngressOutcome,
)
from src.modules.integration.webhooks_inbound.domain.signature import compute_signature
from src.modules.integration.webhooks_inbound.infrastructure.memory import (
    InMemoryDedupStore,
    InMemoryEventInbox,
    InMemoryOrderLocator,
)
from src.modules.sales.ordering.application.adapters import StatusApplier
from src.modules.sales.ordering.application.order_service import OrderService
from src.modules.sales.ordering.domain.aggregate import Order
from src.modules.sales.ordering.projections.projector import OrderProjector
from src.modules.sales.ordering.projections.store import OrderProjectionStore
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.messaging import InMemoryMessageBus
from src.shared.types import ConnectionId, TenantId

_TENANT = TenantId("tnt_demo")
_CONN = "conn_odoo_local"
_SECRET = "whsec_demo"


class FakeSecrets:
    def secret_for(self, connection_id: ConnectionId) -> str | None:
        return _SECRET if str(connection_id) == _CONN else None


def test_observed_order_confirms_via_webhook() -> None:
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    projections = OrderProjectionStore()
    locator = InMemoryOrderLocator()
    bus.subscribe("projections", OrderProjector(projections, locator=locator).handle)

    order_id = OrderService(repo).observe_erp_order(
        tenant_id=_TENANT,
        connection_id=_CONN,
        erp_order_id="S00042",
        client_reference="S00042",
        lines=[ErpPartnerOrderLine(product_key="ANVIL", quantity="3", unit_price="19.99")],
    )
    bus.run_until_empty()

    # routed, delivered to the (stub) ERP, projection reflects it, no ERP identity leaked
    reseller = projections.get_reseller_view(_TENANT, order_id)
    assert reseller is not None and reseller.status == "SENT_TO_ERP"
    operator = projections.get_operator_view(order_id)
    assert operator is not None and operator.owning_connection_id == _CONN
    erp_order_id = operator.erp_order_id
    assert erp_order_id is not None  # locator now knows (conn, erp_order_id) -> order

    # --- inbound ERP webhook: the order was confirmed in Odoo ---
    ingress = InboundWebhookService(
        secrets=FakeSecrets(),
        dedup=InMemoryDedupStore(),
        inbox=InMemoryEventInbox(),
        locator=locator,
        order_status=StatusApplier(repo),
    )
    body = b'{"state":"sale"}'
    outcome = ingress.handle(
        InboundWebhook(
            connection_id=ConnectionId(_CONN),
            erp_type="ODOO",
            erp_order_id=erp_order_id,
            native_fields={"state": "sale"},
            event_ref="evt-1",
            raw_body=body,
            signature=compute_signature(_SECRET, body),
        )
    )
    bus.run_until_empty()  # StatusApplier saved -> OrderConfirmed -> projector updates read model

    assert outcome is IngressOutcome.ACCEPTED
    reseller_after = projections.get_reseller_view(_TENANT, order_id)
    assert reseller_after is not None and reseller_after.status == "CONFIRMED"
    # reseller view still carries no ERP identity
    assert not hasattr(reseller_after, "erp_order_id")
