from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.modules.reference.catalog.application.service import CatalogService
from src.modules.reference.catalog.domain.models import ItemKind
from src.modules.reference.catalog.infrastructure.memory import InMemoryItemRepository
from src.modules.sales.ordering.application.order_service import OrderLineInput, OrderService
from src.modules.sales.ordering.domain.aggregate import Order
from src.modules.sales.ordering.domain.models import OrderLine
from src.modules.sales.ordering.projections.projector import OrderProjector
from src.modules.sales.ordering.projections.store import OrderProjectionStore
from src.modules.sales.quoting.application.service import QuoteService
from src.modules.sales.quoting.domain.errors import PriceNotQuoted
from src.modules.sales.quoting.domain.models import EndCustomer, QuoteLine
from src.modules.sales.quoting.infrastructure.memory import (
    InMemoryOperatingCompanyRepository,
    InMemoryQuoteRepository,
)
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.messaging import InMemoryMessageBus
from src.shared.messaging.facts import CollectingFactPublisher
from src.shared.money import Money
from src.shared.types import ConnectionId, OrderId, TenantId


def _line(product_key: str, qty, line_id: str) -> OrderLine:
    return OrderLine(product_key=product_key, quantity=qty, unit_of_measure="EA", line_id=line_id)


def _wire(items: InMemoryItemRepository | None = None, prices: dict[str, str] | None = None):
    items = items or InMemoryItemRepository()
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    projections = OrderProjectionStore()
    bus.subscribe("projections", OrderProjector(projections).handle)

    quotes = InMemoryQuoteRepository()
    quote_service = QuoteService(quotes, InMemoryOperatingCompanyRepository())
    company = quote_service.create_operating_company(name="Dist", country="US", language="en")
    prices = prices or {"ANVIL": "19.99"}
    quote = quote_service.issue_quote(
        tenant_id=TenantId("tnt_a"),
        operating_company_id=company.operating_company_id,
        end_customer=EndCustomer(name="Downstream", ship_to="1 Main St"),
        currency="USD",
        valid_from=date.today() - timedelta(days=1),
        valid_until=date.today() + timedelta(days=30),
        lines=[
            QuoteLine(product_key=s, unit_price=Money(Decimal(p), "USD"), unit_of_measure="EA")
            for s, p in prices.items()
        ],
    )
    svc = OrderService(repo, quotes, items, quote_service, references=projections)
    return svc, repo, bus, projections, quote.quote_id


def test_reseller_view_reflects_submission_and_hides_erp_identity() -> None:
    svc, _repo, bus, projections, quote_id = _wire()
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"),
        quote_id=quote_id,
        client_reference="PO-1",
        lines=[OrderLineInput("ANVIL", Decimal(2))],
    )
    bus.run_until_empty()

    view = projections.get_reseller_view("tnt_a", order_id)
    assert view is not None
    assert view.client_reference == "PO-1"
    assert view.status == "Submitted"
    assert [line.product_key for line in view.lines] == ["ANVIL"]
    assert view.parties.end_customer_name == "Downstream"  # parties are reseller-safe
    assert view.parties.ship_to == "1 Main St"
    # FR-19: reseller view type has no ERP identity fields at all
    assert not hasattr(view, "owning_connection_id")
    assert not hasattr(view, "erp_order_id")


def test_order_resolves_quote_price_and_projection_computes_subtotal() -> None:
    svc, _repo, bus, projections, quote_id = _wire(prices={"ANVIL": "19.99"})
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"),
        quote_id=quote_id,
        client_reference="PO-1",
        lines=[OrderLineInput("ANVIL", Decimal(2))],
    )
    bus.run_until_empty()

    view = projections.get_reseller_view("tnt_a", order_id)
    assert view is not None
    assert view.lines[0].unit_price == Money(
        Decimal("19.99"), "USD"
    )  # from the quote, not the catalog
    assert view.lines[0].line_total == Money(Decimal("39.98"), "USD")  # 2 * 19.99
    assert view.subtotal == Money(Decimal("39.98"), "USD")


def test_line_not_on_quote_is_refused() -> None:
    svc, _repo, _bus, _projections, quote_id = _wire(prices={"ANVIL": "19.99"})
    with pytest.raises(PriceNotQuoted):
        svc.place_order(
            tenant_id=TenantId("tnt_a"),
            quote_id=quote_id,
            client_reference="PO-1",
            lines=[OrderLineInput("NOT_QUOTED", Decimal(1))],
        )


def test_line_kind_flows_from_catalog_to_projection() -> None:
    items = InMemoryItemRepository()
    CatalogService(items, CollectingFactPublisher()).sync_item(
        sku="LIC",
        name="A License",
        owning_connection_id=ConnectionId("conn_1"),
        kind=ItemKind.LICENSE,
    )
    svc, _repo, bus, projections, quote_id = _wire(items=items, prices={"LIC": "5.00"})
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"),
        quote_id=quote_id,
        client_reference="PO-1",
        lines=[OrderLineInput("LIC", Decimal(1))],
    )
    bus.run_until_empty()
    view = projections.get_reseller_view("tnt_a", order_id)
    assert view is not None
    assert view.lines[0].kind == "LICENSE"


def test_tenant_scoping_blocks_cross_tenant_read() -> None:
    svc, _repo, bus, projections, quote_id = _wire()
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"),
        quote_id=quote_id,
        client_reference="PO-1",
        lines=[OrderLineInput("ANVIL", Decimal(1))],
    )
    bus.run_until_empty()
    assert projections.get_reseller_view("tnt_b", order_id) is None  # other tenant cannot see it


def test_operator_view_exposes_erp_identity_and_timeline() -> None:
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    projections = OrderProjectionStore()
    bus.subscribe("projections", OrderProjector(projections).handle)

    order = Order.submit(
        order_id=OrderId("ord_1"),
        tenant_id=TenantId("tnt_a"),
        client_reference="PO-1",
        lines=[_line("ANVIL", 1, "l_a")],
    )
    order.validate(ConnectionId("conn_1"))
    order.accept()
    order.send_to_erp("S00001")
    repo.save(order)
    bus.run_until_empty()

    operator = projections.get_operator_view("ord_1")
    assert operator is not None
    assert operator.owning_connection_id == "conn_1"
    assert operator.erp_order_id == "S00001"
    assert operator.status == "Sent to ERP"
    assert operator.timeline[-1].status == "Sent to ERP"


def test_projector_feeds_reverse_routing_locator() -> None:
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    projections = OrderProjectionStore()

    recorded: list[tuple[str, str, str]] = []

    class Locator:
        def record(self, connection_id: ConnectionId, erp_order_id: str, order_id: OrderId) -> None:
            recorded.append((str(connection_id), erp_order_id, str(order_id)))

    bus.subscribe("projections", OrderProjector(projections, locator=Locator()).handle)

    order = Order.submit(
        order_id=OrderId("ord_9"),
        tenant_id=TenantId("t"),
        client_reference="r",
        lines=[_line("ANVIL", 1, "l_a")],
    )
    order.validate(ConnectionId("conn_1"))
    order.accept()
    order.send_to_erp("S00099")
    repo.save(order)
    bus.run_until_empty()

    assert recorded == [("conn_1", "S00099", "ord_9")]
