"""Payment domain event — event-sourced, registered with the shared kernel. Split out of
the former `fulfillment` module (class name unchanged, so events stored before the split
still deserialize — the registry is keyed by class name)."""

from __future__ import annotations

from dataclasses import dataclass

from src.shared.eventsourcing import DomainEvent, register_event


@register_event
@dataclass(frozen=True, kw_only=True)
class PaymentRecorded(DomainEvent):
    payment_id: str
    order_id: str
    invoice_id: str | None
    amount: dict[str, str]  # money_to_payload shape: {"amount": str, "currency": str}
    method: str
