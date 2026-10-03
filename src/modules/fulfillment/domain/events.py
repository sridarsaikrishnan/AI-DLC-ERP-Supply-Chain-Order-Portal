"""Domain events for Fulfillment/Invoice/Payment/Return — real event sourcing (ADR-0002's
revisit condition met), registered with the shared kernel so replay works."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.shared.eventsourcing import DomainEvent, register_event


@register_event
@dataclass(frozen=True, kw_only=True)
class FulfillmentRecorded(DomainEvent):
    fulfillment_id: str
    order_id: str
    lines: list[dict[str, Any]]  # [{"line_id": str, "product_key": str, "quantity": str(Decimal)}]
    carrier: str | None = None
    tracking_number: str | None = None
    proof_of_delivery: str | None = None  # Increment 5 (FR-D2) — e.g. a POD reference/signature


@register_event
@dataclass(frozen=True, kw_only=True)
class InvoiceRecorded(DomainEvent):
    invoice_id: str
    order_id: str
    lines: list[dict[str, Any]]  # [{"product_key": str, "quantity": str(Decimal)}]
    erp_invoice_id: str | None = None


@register_event
@dataclass(frozen=True, kw_only=True)
class PaymentRecorded(DomainEvent):
    payment_id: str
    order_id: str
    invoice_id: str | None
    amount: dict[str, str]  # money_to_payload shape: {"amount": str, "currency": str}
    method: str


@register_event
@dataclass(frozen=True, kw_only=True)
class ReturnRecorded(DomainEvent):
    return_id: str
    order_id: str
    lines: list[dict[str, Any]]
    reason_code: str
