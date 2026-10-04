"""Invoice domain event — event-sourced, registered with the shared kernel so replay
works. Split out of the former `fulfillment` module (class name unchanged, so events
stored before the split still deserialize — the registry is keyed by class name)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.shared.eventsourcing import DomainEvent, register_event


@register_event
@dataclass(frozen=True, kw_only=True)
class InvoiceRecorded(DomainEvent):
    invoice_id: str
    order_id: str
    lines: list[dict[str, Any]]  # [{"line_id": str, "product_key": str, "quantity": str(Decimal)}]
    erp_invoice_id: str | None = None
    # Added so the repository can stamp StoredEvent.tenant_id (the webhook-dispatch
    # consumer drops any event with no tenant_id). Defaulted so pre-existing stored
    # events still deserialize.
    tenant_id: str = ""
