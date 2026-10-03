"""OrderService — the write side (commands) for orders."""

from __future__ import annotations

import dataclasses
from typing import Protocol

from src.shared.eventsourcing import EventSourcedRepository
from src.shared.money import Money
from src.shared.types import OrderId, TenantId, generate_id

from ..domain.aggregate import Order
from ..domain.models import OrderLine


class PriceCatalog(Protocol):
    """Narrow lookup `OrderService` needs — not the full `ItemRepository` surface."""

    def find_by_sku(self, sku: str) -> object | None: ...  # duck-typed: .unit_price


class OrderService:
    def __init__(self, repository: EventSourcedRepository[Order], items: PriceCatalog) -> None:
        self._repository = repository
        self._items = items

    def place_order(
        self, *, tenant_id: TenantId, client_reference: str, lines: list[OrderLine]
    ) -> OrderId:
        order_id = OrderId(generate_id("ord"))
        order = Order.submit(
            order_id=order_id,
            tenant_id=tenant_id,
            client_reference=client_reference,
            lines=[self._priced(line) for line in lines],
        )
        self._repository.save(order)
        return order_id

    def _priced(self, line: OrderLine) -> OrderLine:
        """Resolve `unit_price` from the catalog — a reseller's `OrderLineInput` never
        carries a price, and nothing here trusts one even if it did. A SKU not yet synced
        to the catalog (or synced with no price) leaves the line unpriced, same as today —
        that's a `line_total` of `None` downstream, not an order rejection; routing/`UNKNOWN_ITEM`
        is the actual gate for "is this even a real product," handled separately."""
        if line.unit_price is not None:
            return line
        item = self._items.find_by_sku(line.product_key)
        unit_price: Money | None = getattr(item, "unit_price", None)
        if unit_price is None:
            return line
        return dataclasses.replace(line, unit_price=unit_price)

    def cancel_order(self, order_id: OrderId, reason: str) -> None:
        order = self._repository.get(order_id)
        order.cancel(reason)
        self._repository.save(order)
