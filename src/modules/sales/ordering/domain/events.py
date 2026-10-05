"""Order domain events (event-sourced facts). Payloads are primitive/serializable.

Registered with the kernel so `StoredEvent` payloads rehydrate on replay. New fields added
in Increment 5 carry defaults so events stored before the increment still deserialize
(`event_from_stored` does `cls(**payload)` — a pre-increment payload simply omits them).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.shared.eventsourcing import DomainEvent, register_event


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderSubmitted(DomainEvent):
    order_id: str
    tenant_id: str
    client_reference: str
    lines: list[dict[str, Any]]
    product_keys: list[str]
    # Increment 5 (FR-B2/FR-C): the order is a reply to a quote and names its parties.
    # Reseller-safe — no ERP identity here (FR-19).
    quote_id: str = ""
    subsidiary_id: str = ""
    end_customer_name: str = ""
    ship_to: str = ""
    # Increment 7: the quote already decided which ERP connection this order goes to
    # (stamped at quote-issue time, from the issuing subsidiary's route) — no
    # longer derived from line-item ownership at order time.
    routed_to_connection_id: str = ""


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderValidated(DomainEvent):
    """`owning_connection_id` is already known from `OrderSubmitted` (Increment 7) — this
    event just marks that the tenant's binding to it was confirmed verified."""

    order_id: str


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderReadyForDelivery(DomainEvent):
    """Historical event type name kept unchanged (Q2=A) even though the state it drives
    was renamed `READY_FOR_DELIVERY` -> `ACCEPTED` — renaming a persisted event type would
    mean rewriting stored history. It means "routed, ready to send to the ERP".

    Carries `owning_connection_id` directly (even though it's already on `OrderSubmitted`
    too) because `DeliveryHandler` only ever consumes this one event type — it has no
    other way to learn which connection to deliver to without a second lookup."""

    order_id: str
    owning_connection_id: str


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderRejected(DomainEvent):
    order_id: str
    reason_code: str
    reseller_message: str


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderSentToErp(DomainEvent):
    order_id: str
    erp_order_id: str


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderRetrying(DomainEvent):
    order_id: str
    attempt: int
    next_retry_at: str


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderConfirmed(DomainEvent):
    order_id: str


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderFulfilled(DomainEvent):
    """Retained for replay of pre-Increment-5 history ONLY — nothing emits it anymore
    (FULFILLED left the lifecycle, FR-A6). Its apply is a no-op; fulfillment is tracked by
    `OrderLineFulfilled` quantities now."""

    order_id: str


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderClosed(DomainEvent):
    order_id: str


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderCancelled(DomainEvent):
    order_id: str
    reason: str


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderLineFulfilled(DomainEvent):
    """A `Fulfillment` record reported shipping `quantity` of a line. Additive. Increment
    5: keyed on `line_id` (FR-A3) and carries the delivery evidence (`carrier`/
    `proof_of_delivery`) so the order can derive the delivered fact (FR-D2). `product_key`
    is retained (default "") so pre-increment events — which had only `product_key` — still
    deserialize; `line_id` falls back to it on replay."""

    order_id: str
    quantity: str  # str(Decimal) — JSON-safe
    line_id: str = ""
    product_key: str = ""
    carrier: str | None = None
    proof_of_delivery: str | None = None


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderLineInvoiced(DomainEvent):
    """Same shape/reasoning as `OrderLineFulfilled`, for invoicing."""

    order_id: str
    quantity: str
    line_id: str = ""
    product_key: str = ""


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderLineVendorDateSet(DomainEvent):
    """Purchasing bought the line from the maker and recorded the vendor date — that date
    is what "scheduled" means (Increment 5, FR-E1). No Vendor Order document yet (FR-E2)."""

    order_id: str
    line_id: str
    vendor_date: str  # ISO date
