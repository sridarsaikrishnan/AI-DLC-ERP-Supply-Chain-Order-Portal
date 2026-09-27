"""Order domain events (event-sourced facts). Payloads are primitive/serializable.

Registered with the kernel so `StoredEvent` payloads rehydrate on replay.
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


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderValidated(DomainEvent):
    order_id: str
    owning_connection_id: str


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderReadyForDelivery(DomainEvent):
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
