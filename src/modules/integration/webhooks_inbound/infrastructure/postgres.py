"""Postgres-backed dedup store + order locator.

`DedupStore` -> `processed_events` (keyed by a fixed consumer name + the caller's dedup
key). `OrderLocator` -> the `orders` projection's `(owning_connection_id, erp_order_id)`
reverse-routing key, which `PostgresOrderProjectionStore.set_erp_order_id` already
maintains — so this is a read-only view onto that same column.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, LargeBinary, MetaData, String, Table, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.shared.types import ConnectionId, OrderId, generate_id

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

_metadata = MetaData()

processed_events_table = Table(
    "processed_events",
    _metadata,
    Column("consumer", String, primary_key=True),
    Column("event_id", String, primary_key=True),
)

orders_table = Table(
    "orders",
    _metadata,
    Column("order_id", String, primary_key=True),
    Column("owning_connection_id", String),
    Column("erp_order_id", String),
)

erp_event_inbox_table = Table(
    "erp_event_inbox",
    _metadata,
    Column("inbox_id", String, primary_key=True),
    Column("connection_id", String, nullable=False),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("body", LargeBinary, nullable=False),
)

_CONSUMER = "webhooks_inbound"


class PostgresEventInbox:
    """One row per authenticated request. `body` is the raw bytes, unread."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def append(self, connection_id: ConnectionId, body: bytes) -> None:
        session = self._session_factory()
        try:
            session.execute(
                pg_insert(erp_event_inbox_table).values(
                    inbox_id=generate_id("ein"),
                    connection_id=str(connection_id),
                    received_at=datetime.now(UTC),
                    body=body,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class PostgresDedupStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def seen(self, key: str) -> bool:
        session = self._session_factory()
        try:
            row = session.execute(
                select(processed_events_table.c.event_id).where(
                    processed_events_table.c.consumer == _CONSUMER,
                    processed_events_table.c.event_id == key,
                )
            ).first()
            return row is not None
        finally:
            session.close()

    def mark(self, key: str) -> None:
        session = self._session_factory()
        try:
            stmt = pg_insert(processed_events_table).values(consumer=_CONSUMER, event_id=key)
            stmt = stmt.on_conflict_do_nothing(index_elements=["consumer", "event_id"])
            session.execute(stmt)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class PostgresOrderLocator:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def find_order(self, connection_id: ConnectionId, erp_order_id: str) -> OrderId | None:
        session = self._session_factory()
        try:
            row = session.execute(
                select(orders_table.c.order_id).where(
                    orders_table.c.owning_connection_id == str(connection_id),
                    orders_table.c.erp_order_id == erp_order_id,
                )
            ).first()
            return OrderId(row.order_id) if row is not None else None
        finally:
            session.close()

    def record(self, connection_id: ConnectionId, erp_order_id: str, order_id: OrderId) -> None:
        # No-op: `PostgresOrderProjectionStore.set_erp_order_id` already persists this
        # pivot on the `orders` row. Present so this adapter also satisfies the
        # projector's `LocatorSink` protocol if the composition root reuses it there.
        pass
