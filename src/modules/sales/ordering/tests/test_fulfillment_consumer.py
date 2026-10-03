from __future__ import annotations

from decimal import Decimal

from src.modules.sales.ordering.application.fulfillment_consumer import OrderFulfillmentConsumer
from src.modules.sales.ordering.domain.aggregate import Order
from src.modules.sales.ordering.domain.models import (
    DeliveryStatus,
    FulfillmentStatus,
    InvoiceStatus,
    OrderLine,
)
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore, StoredEvent
from src.shared.eventsourcing.events import utcnow
from src.shared.types import ConnectionId, OrderId, TenantId

# The consumer reacts to event-type STRINGS + payload shape, never importing the shipment/
# invoicing modules — so those events are constructed here as plain envelopes, exactly how
# they arrive off the bus/queue. That independence is the point of the saga (ADR-0018).


def _confirmed_order() -> tuple[EventSourcedRepository[Order], str]:
    repo: EventSourcedRepository[Order] = EventSourcedRepository(InMemoryEventStore(), Order)
    order = Order.submit(
        order_id=OrderId("ord_1"),
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-1",
        lines=[
            OrderLine(
                product_key="ANVIL", quantity=Decimal(10), unit_of_measure="EA", line_id="l_a"
            )
        ],
    )
    order.validate(ConnectionId("conn_1"))
    order.accept()
    order.send_to_erp("S001")
    order.confirm()
    repo.save(order)
    return repo, "ord_1"


def _event(event_type: str, payload: dict) -> StoredEvent:
    return StoredEvent(
        stream_id=payload.get("shipment_id") or payload.get("invoice_id") or "x",
        aggregate_type="Shipment" if event_type == "ShipmentRecorded" else "Invoice",
        version=1,
        event_type=event_type,
        event_id=f"evt_{event_type}",
        occurred_at=utcnow(),
        payload=payload,
    )


def test_shipment_recorded_bumps_fulfilled_score() -> None:
    repo, order_id = _confirmed_order()
    consumer = OrderFulfillmentConsumer(repo)

    consumer.handle(
        _event(
            "ShipmentRecorded",
            {
                "shipment_id": "shp_1",
                "order_id": order_id,
                "lines": [{"line_id": "l_a", "quantity": "10"}],
                "carrier": "UPS",
                "proof_of_delivery": None,
            },
        )
    )

    order = repo.get(order_id)
    assert order.fulfillment_status is FulfillmentStatus.FULFILLED
    assert order.delivery_status is DeliveryStatus.DELIVERED  # carrier present -> delivered fact
    assert order.state.value == "CONFIRMED"  # lifecycle untouched


def test_invoice_recorded_bumps_invoiced_score() -> None:
    repo, order_id = _confirmed_order()
    consumer = OrderFulfillmentConsumer(repo)

    consumer.handle(
        _event(
            "InvoiceRecorded",
            {
                "invoice_id": "inv_1",
                "order_id": order_id,
                "lines": [{"line_id": "l_a", "quantity": "4"}],
                "erp_invoice_id": None,
            },
        )
    )

    assert repo.get(order_id).invoice_status is InvoiceStatus.PARTIALLY_INVOICED


def test_unrelated_event_is_ignored() -> None:
    repo, order_id = _confirmed_order()
    consumer = OrderFulfillmentConsumer(repo)
    # a type this consumer doesn't handle must be a no-op, not an error
    consumer.handle(_event("OrderConfirmed", {"order_id": order_id}))
    assert repo.get(order_id).fulfillment_status is FulfillmentStatus.UNFULFILLED
