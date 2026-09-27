"""Wire (de)serialization of StoredEvent for the message bus."""

from __future__ import annotations

import json
from datetime import datetime

from src.shared.eventsourcing import StoredEvent


def to_json(event: StoredEvent) -> str:
    return json.dumps(
        {
            "stream_id": event.stream_id,
            "aggregate_type": event.aggregate_type,
            "version": event.version,
            "event_type": event.event_type,
            "event_id": event.event_id,
            "occurred_at": event.occurred_at.isoformat(),
            "payload": dict(event.payload),
            "tenant_id": event.tenant_id,
            "correlation_id": event.correlation_id,
        }
    )


def from_json(raw: str) -> StoredEvent:
    data = json.loads(raw)
    return StoredEvent(
        stream_id=data["stream_id"],
        aggregate_type=data["aggregate_type"],
        version=int(data["version"]),
        event_type=data["event_type"],
        event_id=data["event_id"],
        occurred_at=datetime.fromisoformat(data["occurred_at"]),
        payload=data.get("payload", {}),
        tenant_id=data.get("tenant_id"),
        correlation_id=data.get("correlation_id"),
    )
