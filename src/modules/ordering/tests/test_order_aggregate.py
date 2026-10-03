from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.ordering.domain.aggregate import Order
from src.modules.ordering.domain.errors import OrderInvalidTransition
from src.modules.ordering.domain.models import OrderLine, OrderState
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.money import Money, TaxRate
from src.shared.types import ConnectionId, OrderId, TenantId


def _lines() -> list[OrderLine]:
    return [OrderLine(product_key="ANVIL", quantity=2, unit_of_measure="EA")]


def _order() -> Order:
    return Order.submit(
        order_id=OrderId("ord_1"),
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-1",
        lines=_lines(),
    )


def test_submit_sets_state_and_derives_product_keys() -> None:
    order = _order()
    assert order.state is OrderState.SUBMITTED
    assert order.product_keys == ["ANVIL"]
    assert order.has_pending


def test_submit_rejects_empty_or_nonpositive_lines() -> None:
    with pytest.raises(ValueError):
        Order.submit(order_id=OrderId("o"), tenant_id=TenantId("t"), client_reference="r", lines=[])
    with pytest.raises(ValueError):
        Order.submit(
            order_id=OrderId("o"),
            tenant_id=TenantId("t"),
            client_reference="r",
            lines=[OrderLine(product_key="X", quantity=0, unit_of_measure="EA")],
        )


def test_happy_path_lifecycle() -> None:
    order = _order()
    order.validate(ConnectionId("conn_1"))
    order.mark_ready_for_delivery()
    order.send_to_erp("S00001")
    order.confirm()
    order.fulfill()
    order.close()
    assert order.state is OrderState.CLOSED
    assert order.owning_connection_id == ConnectionId("conn_1")
    assert order.erp_order_id == "S00001"


def test_invalid_transition_raises() -> None:
    order = _order()
    with pytest.raises(OrderInvalidTransition):
        order.confirm()  # cannot confirm a freshly submitted order


def test_confirm_is_idempotent() -> None:
    order = _order()
    order.validate(ConnectionId("conn_1"))
    order.mark_ready_for_delivery()
    order.send_to_erp("S1")
    order.confirm()
    order.collect_events()
    order.confirm()  # repeat -> no-op, no new event
    assert order.collect_events() == []


def test_cannot_cancel_fulfilled_order() -> None:
    order = _order()
    order.validate(ConnectionId("conn_1"))
    order.mark_ready_for_delivery()
    order.send_to_erp("S1")
    order.confirm()
    order.fulfill()
    with pytest.raises(OrderInvalidTransition):
        order.cancel("changed mind")


def test_event_sourced_round_trip_via_repository() -> None:
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order)
    order = _order()
    order.validate(ConnectionId("conn_1"))
    order.mark_ready_for_delivery()
    repo.save(order)

    reloaded = repo.get("ord_1")
    assert reloaded.state is OrderState.READY_FOR_DELIVERY
    assert reloaded.owning_connection_id == ConnectionId("conn_1")
    assert reloaded.client_reference == "PO-1"
    assert reloaded.version == order.version


def test_quantity_is_decimal_and_survives_event_replay_exactly() -> None:
    # The bug this guards against: a float round-trip through JSON can perturb a value
    # like 2.1 (binary float can't represent it exactly). Decimal, serialized as str in
    # the event payload (aggregate.py), must come back bit-for-bit identical.
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order)
    order = Order.submit(
        order_id=OrderId("ord_2"),
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-2",
        lines=[OrderLine(product_key="ANVIL", quantity=Decimal("2.1"), unit_of_measure="EA")],
    )
    assert isinstance(order.lines[0].quantity, Decimal)
    repo.save(order)

    reloaded = repo.get("ord_2")
    assert reloaded.lines[0].quantity == Decimal("2.1")
    assert isinstance(reloaded.lines[0].quantity, Decimal)


def test_priced_line_survives_event_replay_exactly() -> None:
    # Phase 2: unit_price/line_discount/tax_rates must round-trip through the JSONB-safe
    # payload (money_to_payload/from_payload, tax_rate_to_payload/from_payload) exactly
    # as Decimal, same guard as Phase 1's quantity test but for the new nested fields.
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order)
    order = Order.submit(
        order_id=OrderId("ord_3"),
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-3",
        lines=[
            OrderLine(
                product_key="ANVIL",
                quantity=Decimal("2.5"),
                unit_of_measure="EA",
                unit_price=Money(Decimal("19.99"), "USD"),
                line_discount=Money(Decimal("1.50"), "USD"),
                tax_rates=[TaxRate("VAT", Decimal("0.20"), inclusive=False)],
            )
        ],
    )
    repo.save(order)

    reloaded = repo.get("ord_3")
    line = reloaded.lines[0]
    assert line.unit_price == Money(Decimal("19.99"), "USD")
    assert line.line_discount == Money(Decimal("1.50"), "USD")
    assert line.tax_rates == [TaxRate("VAT", Decimal("0.20"), inclusive=False)]


def test_snapshot_round_trip() -> None:
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, snapshot_every=1)
    order = _order()
    repo.save(order)
    assert store.load_snapshot("ord_1") is not None
    assert repo.get("ord_1").state is OrderState.SUBMITTED
