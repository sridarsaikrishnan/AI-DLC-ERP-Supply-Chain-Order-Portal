"""SQLAlchemy Core table definitions matching migration 0001 (event store + outbox)."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

events_table = Table(
    "events",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("stream_id", String, nullable=False),
    Column("aggregate_type", String, nullable=False),
    Column("version", Integer, nullable=False),
    Column("event_type", String, nullable=False),
    Column("event_id", String, nullable=False, unique=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("tenant_id", String),
    Column("correlation_id", String),
    Column("payload", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    UniqueConstraint("stream_id", "version", name="uq_events_stream_version"),
)

snapshots_table = Table(
    "snapshots",
    metadata,
    Column("stream_id", String, primary_key=True),
    Column("version", Integer, nullable=False),
    Column("state", JSONB, nullable=False),
    Column("taken_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
)

outbox_table = Table(
    "outbox",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("event_id", String, nullable=False),
    Column("event_type", String, nullable=False),
    Column("stream_id", String, nullable=False),
    Column("aggregate_type", String, nullable=False),
    Column("tenant_id", String),
    Column("correlation_id", String),
    Column("payload", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("occurred_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("published_at", DateTime(timezone=True)),
)
