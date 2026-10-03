"""OrderService — the write side (commands) for orders.

An order is a reply to a quote (Increment 5, FR-B2): placement resolves every line's
price from the referenced quote and refuses a line with no quoted price (FR-B3). The
catalog is consulted only for the line's kind (box/license, FR-D1) — never for price.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Protocol

from src.modules.quoting.domain.errors import PriceNotQuoted, QuoteNotFound, QuoteNotValid
from src.shared.types import OrderId, TenantId, generate_id

from ..domain.aggregate import Order
from ..domain.models import KIND_PHYSICAL, OrderLine

if TYPE_CHECKING:
    from decimal import Decimal

    from src.modules.quoting.domain.models import Quote
    from src.shared.eventsourcing import EventSourcedRepository


@dataclass(frozen=True)
class OrderLineInput:
    """What a reseller supplies when replying to a quote: a SKU and a quantity. No price —
    price comes from the quote, never from the client (ADR-0016, continuing ADR-0011's
    never-trust-the-client stance)."""

    product_key: str
    quantity: Decimal


class QuoteDirectory(Protocol):
    def get(self, quote_id: str) -> Quote | None: ...


class ItemKindLookup(Protocol):
    """Narrow lookup for a line's kind (box/license) — not the full `ItemRepository`."""

    def find_by_sku(self, sku: str) -> object | None: ...  # duck-typed: .kind


class QuoteAcceptor(Protocol):
    def mark_accepted(self, quote_id: str) -> None: ...


class OrderService:
    def __init__(
        self,
        repository: EventSourcedRepository[Order],
        quotes: QuoteDirectory,
        items: ItemKindLookup,
        quote_acceptor: QuoteAcceptor | None = None,
    ) -> None:
        self._repository = repository
        self._quotes = quotes
        self._items = items
        self._quote_acceptor = quote_acceptor

    def place_order(
        self,
        *,
        tenant_id: TenantId,
        quote_id: str,
        client_reference: str,
        lines: list[OrderLineInput],
        today: date | None = None,
    ) -> OrderId:
        quote = self._quotes.get(quote_id)
        if quote is None or quote.tenant_id != tenant_id:
            raise QuoteNotFound(quote_id)
        if not quote.is_valid_on(today or date.today()):
            raise QuoteNotValid(quote_id)
        if not lines:
            raise ValueError("order must have at least one line")

        order_lines = [self._line_from_quote(quote, inp) for inp in lines]
        order_id = OrderId(generate_id("ord"))
        order = Order.submit(
            order_id=order_id,
            tenant_id=tenant_id,
            client_reference=client_reference,
            lines=order_lines,
            quote_id=quote.quote_id,
            operating_company_id=quote.operating_company_id,
            end_customer_name=quote.end_customer.name,
            ship_to=quote.end_customer.ship_to,
        )
        self._repository.save(order)
        if self._quote_acceptor is not None:
            self._quote_acceptor.mark_accepted(quote.quote_id)
        return order_id

    def _line_from_quote(self, quote: Quote, inp: OrderLineInput) -> OrderLine:
        quote_line = quote.find_line(inp.product_key)
        if quote_line is None:
            raise PriceNotQuoted(inp.product_key)  # FR-B3: no quoted price -> refused
        item = self._items.find_by_sku(inp.product_key)
        kind = getattr(item, "kind", None)
        kind_str = kind.value if kind is not None else KIND_PHYSICAL
        return OrderLine(
            product_key=inp.product_key,
            quantity=inp.quantity,
            unit_of_measure=quote_line.unit_of_measure,
            line_id=generate_id("ol"),
            kind=kind_str,
            unit_price=quote_line.unit_price,
            line_discount=quote_line.line_discount,
            tax_rates=[quote_line.tax_rate] if quote_line.tax_rate is not None else [],
        )

    def cancel_order(self, order_id: OrderId, reason: str) -> None:
        order = self._repository.get(order_id)
        order.cancel(reason)
        self._repository.save(order)
