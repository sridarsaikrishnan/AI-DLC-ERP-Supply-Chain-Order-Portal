"""ShipmentService — records a shipment (dispatch: carrier/tracking/POD) and, in the same
transaction, bumps the order's fulfilled-quantity score (FR-A4). On Postgres both appends
share one session via the injected `UnitOfWork`; in memory it's a no-op. Lines are keyed by
`line_id` (FR-A3).

Commit 1 keeps this synchronous Shipment -> Order coupling unchanged from the former
`FulfillmentService`; the event-driven saga (ordering consumes `ShipmentRecorded` instead
of this service touching the order directly) lands in commit 2.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from src.shared.types import generate_id
from src.shared.unit_of_work import NullUnitOfWork, UnitOfWork

from ..domain.aggregate import Shipment

if TYPE_CHECKING:
    from src.modules.sales.ordering.domain.aggregate import Order
    from src.shared.eventsourcing import EventSourcedRepository


def _line_id(line: dict[str, Any]) -> str:
    return str(line.get("line_id") or line.get("product_key") or "")


class ShipmentService:
    def __init__(
        self,
        shipments: EventSourcedRepository[Shipment],
        orders: EventSourcedRepository[Order],
        uow: UnitOfWork | None = None,
    ) -> None:
        self._shipments = shipments
        self._orders = orders
        self._uow = uow or NullUnitOfWork()

    def record(
        self,
        *,
        order_id: str,
        lines: list[dict[str, Any]],
        carrier: str | None = None,
        tracking_number: str | None = None,
        proof_of_delivery: str | None = None,
    ) -> Shipment:
        shipment = Shipment.record(
            shipment_id=generate_id("shp"),
            order_id=order_id,
            lines=lines,
            carrier=carrier,
            tracking_number=tracking_number,
            proof_of_delivery=proof_of_delivery,
        )
        with self._uow.atomic():
            self._shipments.save(shipment)
            order = self._orders.get(order_id)
            for line in lines:
                order.record_fulfillment(
                    _line_id(line),
                    Decimal(str(line["quantity"])),
                    carrier=carrier,
                    proof_of_delivery=proof_of_delivery,
                )
            self._orders.save(order)
        return shipment
