"""OrderService — the write side (commands) for orders.

Orders are sales orders that already exist in the ERP. `observe_erp_order` adopts one.
Nothing here creates a quote or a purchase order.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Protocol

from src.shared.eventsourcing import AggregateNotFound
from src.shared.money import Money
from src.shared.types import OrderId, TenantId

from ..domain.aggregate import Order
from ..domain.models import OrderLine

if TYPE_CHECKING:
    from src.shared.eventsourcing import EventSourcedRepository


class ObservedLine(Protocol):
    """A product line the ERP adapter already translated. Sales does not import it."""

    product_key: str
    quantity: str
    unit_price: str
    currency: str


class OrderService:
    def __init__(self, repository: EventSourcedRepository[Order]) -> None:
        self._repository = repository

    def observe_erp_order(
        self,
        *,
        tenant_id: TenantId,
        connection_id: str,
        erp_order_id: str,
        client_reference: str,
        lines: list[ObservedLine] | tuple[ObservedLine, ...],
        subsidiary_id: str,
    ) -> OrderId | None:
        """Adopt `erp_order_id` if we have not already. The id is stable so a second poll
        is a no-op even before the projection has caught up.

        Returns None when the company on the quotation is not a known subsidiary, or when
        the document has no product line we can follow.
        """
        order_id = OrderId(f"ord_{connection_id}_{erp_order_id}")
        try:
            self._repository.get(str(order_id))
        except AggregateNotFound:
            pass
        else:
            return order_id

        if not subsidiary_id:
            return None

        order_lines: list[OrderLine] = []
        for index, line in enumerate(lines, start=1):
            if not line.product_key:
                continue
            quantity = Decimal(str(line.quantity))
            if quantity <= 0:
                continue
            price = None
            if line.unit_price not in ("", None):
                price = Money(Decimal(str(line.unit_price)), line.currency or "USD")
            order_lines.append(
                OrderLine(
                    product_key=line.product_key,
                    quantity=quantity,
                    unit_of_measure="",
                    line_id=f"{order_id}_{index}",
                    unit_price=price,
                )
            )
        if not order_lines:
            return None
        order = Order.observe(
            order_id=order_id,
            tenant_id=tenant_id,
            client_reference=client_reference or erp_order_id,
            lines=order_lines,
            connection_id=connection_id,
            erp_order_id=erp_order_id,
            subsidiary_id=subsidiary_id,
        )
        self._repository.save(order)
        return order_id

    def cancel_order(self, order_id: OrderId, reason: str) -> None:
        order = self._repository.get(order_id)
        order.cancel(reason)
        self._repository.save(order)
