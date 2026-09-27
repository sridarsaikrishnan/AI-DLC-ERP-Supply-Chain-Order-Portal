from __future__ import annotations

from datetime import datetime, timezone

from src.shared.eventsourcing import StoredEvent
from src.shared.messaging.envelope import from_json, to_json


def test_stored_event_json_round_trip() -> None:
    event = StoredEvent(
        stream_id="ord_1",
        aggregate_type="Order",
        version=2,
        event_type="OrderValidated",
        event_id="evt_1",
        occurred_at=datetime(2026, 9, 22, 10, 0, 0, tzinfo=timezone.utc),
        payload={"order_id": "ord_1", "owning_connection_id": "conn_1"},
        tenant_id="tnt_a",
        correlation_id="corr_1",
    )
    restored = from_json(to_json(event))
    assert restored == event
