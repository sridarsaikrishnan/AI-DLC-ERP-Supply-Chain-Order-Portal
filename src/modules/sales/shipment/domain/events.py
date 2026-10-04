"""Shipment domain event — event-sourced, registered with the shared kernel.

Renamed from `FulfillmentRecorded` to `ShipmentRecorded` when `fulfillment` was split into
`sales/shipment` (the aggregate records a dispatch — carrier/tracking/POD — which is a
shipment; "delivered" is a downstream status, see ADR on the split).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.shared.eventsourcing import DomainEvent, register_event


@register_event
@dataclass(frozen=True, kw_only=True)
class ShipmentRecorded(DomainEvent):
    shipment_id: str
    order_id: str
    lines: list[dict[str, Any]]  # [{"line_id": str, "product_key": str, "quantity": str(Decimal)}]
    carrier: str | None = None
    tracking_number: str | None = None
    proof_of_delivery: str | None = None  # (FR-D2) — a POD reference/signature
    # Added so the repository can stamp StoredEvent.tenant_id (the webhook-dispatch
    # consumer drops any event with no tenant_id). Defaulted so pre-existing stored
    # events still deserialize.
    tenant_id: str = ""
