"""Event-sourcing kernel (shared).

A small, dependency-free core used by domain services. Public API:

    from src.shared.eventsourcing import (
        DomainEvent, StoredEvent, register_event,
        Aggregate, EventSourcedRepository,
        EventStore, InMemoryEventStore,
        Outbox, InMemoryOutbox,
        EventPublisher, CollectingPublisher, NullEventPublisher,
        Snapshot,
        ConcurrencyError, AggregateNotFound, UnknownEventType, UnhandledEvent,
    )

Design rules (see README.md): behavior lives in aggregates; state changes only via
events; the store enforces optimistic concurrency; this package imports nothing from
`modules`, `api`, `worker`, or any cloud SDK.
"""

from __future__ import annotations

from .aggregate import Aggregate
from .errors import (
    AggregateNotFound,
    ConcurrencyError,
    EventSourcingError,
    UnhandledEvent,
    UnknownEventType,
)
from .events import DomainEvent, StoredEvent, new_id, utcnow
from .outbox import InMemoryOutbox, Outbox
from .publisher import CollectingPublisher, EventPublisher, NullEventPublisher
from .repository import EventSourcedRepository, MetadataProvider
from .serialization import event_from_stored, event_type_name, register_event, to_payload
from .snapshots import Snapshot
from .store import EventStore, InMemoryEventStore

__all__ = [
    "Aggregate",
    "AggregateNotFound",
    "CollectingPublisher",
    "ConcurrencyError",
    "DomainEvent",
    "EventPublisher",
    "EventSourcedRepository",
    "EventSourcingError",
    "EventStore",
    "InMemoryEventStore",
    "InMemoryOutbox",
    "MetadataProvider",
    "NullEventPublisher",
    "Outbox",
    "Snapshot",
    "StoredEvent",
    "UnhandledEvent",
    "UnknownEventType",
    "event_from_stored",
    "event_type_name",
    "new_id",
    "register_event",
    "to_payload",
    "utcnow",
]
