"""ShipmentService — records a shipment (dispatch: carrier/tracking/POD) and nothing else.

The shipment's `ShipmentRecorded` event is published; the order's fulfilled-quantity score
is bumped asynchronously by the ordering saga consumer that reacts to that event (ADR-0018),
not by this service reaching into the Order aggregate. That decoupling is what lets
`shipment` be extracted from `ordering` without a shared write transaction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.shared.types import generate_id

from ..domain.aggregate import Shipment

if TYPE_CHECKING:
    from src.shared.eventsourcing import EventSourcedRepository


class ShipmentService:
    def __init__(self, shipments: EventSourcedRepository[Shipment]) -> None:
        self._shipments = shipments

    def record(
        self,
        *,
        order_id: str,
        lines: list[dict[str, Any]],
        carrier: str | None = None,
        tracking_number: str | None = None,
        proof_of_delivery: str | None = None,
        tenant_id: str = "",
    ) -> Shipment:
        shipment = Shipment.record(
            shipment_id=generate_id("shp"),
            order_id=order_id,
            lines=lines,
            carrier=carrier,
            tracking_number=tracking_number,
            proof_of_delivery=proof_of_delivery,
            tenant_id=tenant_id,
        )
        self._shipments.save(shipment)
        return shipment
