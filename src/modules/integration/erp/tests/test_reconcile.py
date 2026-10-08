from __future__ import annotations

from src.modules.integration.erp.application.ports import ErpShipment, ErpShipmentLine, ErpTarget
from src.modules.integration.erp.application.reconcile import ReconcileSweeper
from src.modules.integration.erp.domain.status_mapping import CanonicalStatus
from src.modules.integration.erp.infrastructure.stub_adapter import StubErpAdapter
from src.modules.integration.webhooks_inbound.infrastructure.memory import InMemoryOrderLocator
from src.shared.types import ConnectionId, OrderId

_CONN = ConnectionId("conn_1")


class FakeConnections:
    def resolve(self, connection_id: ConnectionId) -> ErpTarget | None:
        return ErpTarget(
            erp_type="ODOO",
            base_url="http://odoo",
            credentials={"database": "odoo", "username": "admin"},
            secret="x",
        )


class RecordingStatus:
    def __init__(self) -> None:
        self.applied: list[tuple[str, CanonicalStatus]] = []

    def apply_status(self, order_id: OrderId, status: CanonicalStatus) -> None:
        self.applied.append((order_id, status))


def test_reconcile_applies_status_for_known_orders() -> None:
    adapter = StubErpAdapter()
    target = FakeConnections().resolve(_CONN)
    assert target is not None
    erp_order_id = adapter.submit(target, {}).erp_order_id  # status seeded as "sale"
    assert erp_order_id is not None

    locator = InMemoryOrderLocator()
    locator.record(_CONN, erp_order_id, OrderId("ord_1"))
    status = RecordingStatus()

    sweeper = ReconcileSweeper(
        connections=FakeConnections(),
        adapter_for=lambda _t: adapter,
        locator=locator,
        order_status=status,
    )
    applied = sweeper.run(_CONN, [erp_order_id])

    assert applied == 1
    assert status.applied == [("ord_1", CanonicalStatus.CONFIRMED)]


def test_reconcile_passes_erp_shipments_to_the_sync() -> None:
    adapter = StubErpAdapter()
    target = FakeConnections().resolve(_CONN)
    assert target is not None
    erp_order_id = adapter.submit(target, {}).erp_order_id
    assert erp_order_id is not None
    shipment = ErpShipment(
        erp_shipment_id="9",
        lines=(ErpShipmentLine(product_key="ANVIL", quantity="2"),),
        proof_of_delivery="WH/OUT/00009",
    )
    adapter.fetch_shipments = lambda _target, _erp_order_id: [shipment]  # type: ignore[method-assign]

    locator = InMemoryOrderLocator()
    locator.record(_CONN, erp_order_id, OrderId("ord_1"))
    seen: list[tuple[str, list[ErpShipment]]] = []

    sweeper = ReconcileSweeper(
        connections=FakeConnections(),
        adapter_for=lambda _t: adapter,
        locator=locator,
        order_status=RecordingStatus(),
        sync_shipments=lambda order_id, shipments: seen.append((order_id, shipments)),
    )
    sweeper.run(_CONN, [erp_order_id])

    assert seen == [("ord_1", [shipment])]
