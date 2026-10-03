"""End-to-end write path: place_order (reply to a quote) -> OrderSubmitted on the bus ->
OrderProcessor routes -> order becomes ACCEPTED (or REJECTED). In-memory store + bus.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.modules.catalog.infrastructure.memory import InMemoryItemRepository
from src.modules.ordering.application.order_service import OrderLineInput, OrderService
from src.modules.ordering.application.processing import OrderProcessor
from src.modules.ordering.domain.aggregate import Order
from src.modules.ordering.domain.models import OrderState
from src.modules.quoting.application.service import QuoteService
from src.modules.quoting.domain.models import EndCustomer, QuoteLine
from src.modules.quoting.infrastructure.memory import (
    InMemoryOperatingCompanyRepository,
    InMemoryQuoteRepository,
)
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore
from src.shared.messaging import InMemoryMessageBus
from src.shared.money import Money
from src.shared.types import ConnectionId, TenantId


class FakeOwnership:
    def __init__(self, owners: dict[str, str]) -> None:
        self._owners = owners

    def owner_of(self, product_key: str) -> ConnectionId | None:
        value = self._owners.get(product_key)
        return ConnectionId(value) if value else None


class FakeBindings:
    def __init__(self, bound: set[tuple[str, str]]) -> None:
        self._bound = bound

    def is_bound(self, tenant_id: TenantId, connection_id: ConnectionId) -> bool:
        return (str(tenant_id), str(connection_id)) in self._bound


def _wire(owners: dict[str, str], bound: set[tuple[str, str]], skus: list[str]):
    store = InMemoryEventStore()
    bus = InMemoryMessageBus()
    repo: EventSourcedRepository[Order] = EventSourcedRepository(store, Order, publisher=bus)
    processor = OrderProcessor(repo, FakeOwnership(owners), FakeBindings(bound))
    bus.subscribe("order-processing", processor.handle, event_types={"OrderSubmitted"})

    quotes = InMemoryQuoteRepository()
    companies = InMemoryOperatingCompanyRepository()
    quote_service = QuoteService(quotes, companies)
    company = quote_service.create_operating_company(name="Distributor Co", country="US", language="en")
    quote = quote_service.issue_quote(
        tenant_id=TenantId("tnt_a"),
        operating_company_id=company.operating_company_id,
        end_customer=EndCustomer(name="Downstream", ship_to="1 Main St"),
        currency="USD",
        valid_from=date.today() - timedelta(days=1),
        valid_until=date.today() + timedelta(days=30),
        lines=[QuoteLine(product_key=s, unit_price=Money(Decimal("10.00"), "USD"), unit_of_measure="EA") for s in skus],
    )
    service = OrderService(repo, quotes, InMemoryItemRepository(), quote_service)
    return service, repo, bus, quote.quote_id


def test_place_order_routes_to_owning_connection() -> None:
    svc, repo, bus, quote_id = _wire({"ANVIL": "conn_1"}, {("tnt_a", "conn_1")}, ["ANVIL"])
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"), quote_id=quote_id, client_reference="PO-1",
        lines=[OrderLineInput("ANVIL", Decimal(1))],
    )
    bus.run_until_empty()

    order = repo.get(order_id)
    assert order.state is OrderState.ACCEPTED
    assert order.owning_connection_id == ConnectionId("conn_1")


def test_place_order_mixed_erp_is_rejected() -> None:
    svc, repo, bus, quote_id = _wire(
        {"ANVIL": "conn_1", "ROCKET": "conn_2"},
        {("tnt_a", "conn_1"), ("tnt_a", "conn_2")},
        ["ANVIL", "ROCKET"],
    )
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"), quote_id=quote_id, client_reference="PO-2",
        lines=[OrderLineInput("ANVIL", Decimal(1)), OrderLineInput("ROCKET", Decimal(1))],
    )
    bus.run_until_empty()

    assert repo.get(order_id).state is OrderState.REJECTED


def test_place_order_without_binding_is_rejected() -> None:
    svc, repo, bus, quote_id = _wire({"ANVIL": "conn_1"}, set(), ["ANVIL"])  # no verified binding
    order_id = svc.place_order(
        tenant_id=TenantId("tnt_a"), quote_id=quote_id, client_reference="PO-3",
        lines=[OrderLineInput("ANVIL", Decimal(1))],
    )
    bus.run_until_empty()
    assert repo.get(order_id).state is OrderState.REJECTED
