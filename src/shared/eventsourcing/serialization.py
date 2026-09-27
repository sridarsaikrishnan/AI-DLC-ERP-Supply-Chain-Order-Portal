"""Event (de)serialization via a small type registry.

Keeps the kernel free of any specific serializer. Domain events register their class
so `StoredEvent` payloads can be rehydrated on replay.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, TypeVar

from .errors import UnknownEventType
from .events import DomainEvent, StoredEvent

_registry: dict[str, type[DomainEvent]] = {}

_META_FIELDS = frozenset({"event_id", "occurred_at"})

E = TypeVar("E", bound=DomainEvent)


def register_event(cls: type[E]) -> type[E]:
    """Class decorator: register a domain event type by its class name."""
    _registry[cls.__name__] = cls
    return cls


def event_type_name(event: DomainEvent) -> str:
    return type(event).__name__


def to_payload(event: DomainEvent) -> dict[str, Any]:
    """Domain fields only (envelope metadata is stored separately on StoredEvent)."""
    return {k: v for k, v in asdict(event).items() if k not in _META_FIELDS}


def event_from_stored(stored: StoredEvent) -> DomainEvent:
    cls = _registry.get(stored.event_type)
    if cls is None:
        raise UnknownEventType(stored.event_type)
    return cls(event_id=stored.event_id, occurred_at=stored.occurred_at, **stored.payload)
