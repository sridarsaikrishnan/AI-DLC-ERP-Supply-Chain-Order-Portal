"""Return domain event — event-sourced, registered with the shared kernel. Split out of
the former `fulfillment` module (class name unchanged, so events stored before the split
still deserialize — the registry is keyed by class name)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.shared.eventsourcing import DomainEvent, register_event


@register_event
@dataclass(frozen=True, kw_only=True)
class ReturnRecorded(DomainEvent):
    return_id: str
    order_id: str
    lines: list[dict[str, Any]]
    reason_code: str
