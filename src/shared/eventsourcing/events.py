"""Event types: the domain-facing `DomainEvent` and the storage/transport envelope `StoredEvent`."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base for all domain events — an immutable fact.

    Subclass as a frozen, kw-only dataclass and add domain fields, then register it::

        @register_event
        @dataclass(frozen=True, kw_only=True)
        class OrderSubmitted(DomainEvent):
            order_id: str
            tenant_id: str

    `event_id` and `occurred_at` are envelope metadata every event carries.
    """

    event_id: str = field(default_factory=new_id)
    occurred_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class StoredEvent:
    """A domain event as persisted/transported: payload + routing/ordering metadata.

    This is the on-the-wire envelope (also what the outbox and message bus carry).
    `payload` holds only the domain fields; envelope metadata is lifted out.
    """

    stream_id: str
    aggregate_type: str
    version: int
    event_type: str
    event_id: str
    occurred_at: datetime
    payload: Mapping[str, Any]
    tenant_id: str | None = None
    correlation_id: str | None = None
