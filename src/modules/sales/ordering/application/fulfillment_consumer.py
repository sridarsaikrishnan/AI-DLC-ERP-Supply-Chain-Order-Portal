"""OrderFulfillmentConsumer — the ordering side of the shipment/invoice saga (ADR-0018).

Reacts to `ShipmentRecorded` / `InvoiceRecorded` and bumps the order's shipped/invoiced
quantity scores. It depends only on the *event-type strings and payload shape*, never on
the `shipment`/`invoicing` modules — so those modules can be extracted without ordering
importing them. This is the `order-fulfillment` consumer's logic.

Idempotency: `record_fulfillment`/`record_invoice` are additive, so at-least-once
redelivery would double-count. The worker wraps this handler with an `event_id` dedupe
against `processed_events` (and the in-memory bus dedupes per consumer), the same
guarantee every other consumer relies on.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared.eventsourcing import EventSourcedRepository, StoredEvent

    from ..domain.aggregate import Order


def _line_id(line: dict[str, Any]) -> str:
    return str(line.get("line_id") or line.get("product_key") or "")


class OrderFulfillmentConsumer:
    def __init__(self, repository: EventSourcedRepository[Order]) -> None:
        self._repository = repository

    def handle(self, event: StoredEvent) -> None:
        if event.event_type == "ShipmentRecorded":
            self._apply_shipment(event)
        elif event.event_type == "InvoiceRecorded":
            self._apply_invoice(event)

    def _apply_shipment(self, event: StoredEvent) -> None:
        payload = event.payload
        order = self._repository.get(str(payload["order_id"]))
        carrier = payload.get("carrier")
        proof_of_delivery = payload.get("proof_of_delivery")
        for line in payload["lines"]:
            order.record_fulfillment(
                _line_id(line),
                Decimal(str(line["quantity"])),
                carrier=carrier,
                proof_of_delivery=proof_of_delivery,
            )
        self._repository.save(order)

    def _apply_invoice(self, event: StoredEvent) -> None:
        payload = event.payload
        order = self._repository.get(str(payload["order_id"]))
        for line in payload["lines"]:
            order.record_invoice(_line_id(line), Decimal(str(line["quantity"])))
        self._repository.save(order)
