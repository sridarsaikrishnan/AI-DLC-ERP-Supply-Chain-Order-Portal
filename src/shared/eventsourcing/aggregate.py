"""Aggregate root base.

Behavior lives in the aggregate (not in services) — services orchestrate, the aggregate
decides and records events. State changes happen ONLY by applying events, so replay
reconstructs state exactly.

Event handling uses an explicit `_apply_<EventClassName>` convention — no shared dispatch
registry (which would leak handlers across aggregate types).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from .errors import UnhandledEvent

if TYPE_CHECKING:
    from .events import DomainEvent


class Aggregate:
    aggregate_type: ClassVar[str] = "Aggregate"

    def __init__(self, id: str) -> None:
        self.id: str = id
        self.version: int = 0
        self._pending: list[DomainEvent] = []

    def apply(self, event: DomainEvent) -> None:
        """Mutate state from an event. Used for both replay and newly emitted events."""
        handler = getattr(self, f"_apply_{type(event).__name__}", None)
        if handler is None:
            raise UnhandledEvent(
                f"{type(self).__name__} has no handler _apply_{type(event).__name__}"
            )
        handler(event)

    def emit(self, event: DomainEvent) -> None:
        """Record a NEW event: apply it, bump version, queue it for persistence."""
        self.apply(event)
        self.version += 1
        self._pending.append(event)

    def collect_events(self) -> list[DomainEvent]:
        """Return and clear pending events (called by the repository on save)."""
        pending = self._pending
        self._pending = []
        return pending

    @property
    def has_pending(self) -> bool:
        return bool(self._pending)

    # --- optional snapshot hooks (override in aggregates that opt into snapshots) ---
    def snapshot_state(self) -> dict[str, Any] | None:
        return None

    def restore(self, state: dict[str, Any]) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not support snapshots")
