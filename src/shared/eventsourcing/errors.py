"""Kernel error types."""

from __future__ import annotations


class EventSourcingError(Exception):
    """Base class for all event-sourcing kernel errors."""


class ConcurrencyError(EventSourcingError):
    """Raised when the expected stream version does not match the store (optimistic lock)."""

    def __init__(self, stream_id: str, expected: int, actual: int) -> None:
        super().__init__(
            f"concurrency conflict on stream '{stream_id}': expected version {expected}, found {actual}"
        )
        self.stream_id = stream_id
        self.expected = expected
        self.actual = actual


class AggregateNotFound(EventSourcingError):
    """Raised when an aggregate has no events and no snapshot."""

    def __init__(self, aggregate_id: str) -> None:
        super().__init__(f"aggregate '{aggregate_id}' not found")
        self.aggregate_id = aggregate_id


class UnknownEventType(EventSourcingError):
    """Raised when deserializing an event type that was never registered."""

    def __init__(self, event_type: str) -> None:
        super().__init__(f"unknown event type '{event_type}' (did you @register_event it?)")
        self.event_type = event_type


class UnhandledEvent(EventSourcingError):
    """Raised when an aggregate has no `_apply_<EventName>` handler for an event."""
