"""Postgres-backed item repository — the `ItemRepository` port on `items`."""

from __future__ import annotations

from sqlalchemy import Column, MetaData, String, Table, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session, sessionmaker

from src.shared.types import ConnectionId, ItemId

from ..domain.models import Item

_metadata = MetaData()

items_table = Table(
    "items",
    _metadata,
    Column("item_id", String, primary_key=True),
    Column("sku", String, nullable=False, unique=True),
    Column("name", String, nullable=False),
    Column("owning_connection_id", String, nullable=False),
)


def _to_model(row: Row) -> Item:
    return Item(
        item_id=ItemId(row.item_id),
        sku=row.sku,
        name=row.name,
        owning_connection_id=ConnectionId(row.owning_connection_id),
    )


class PostgresItemRepository:
    """`ItemRepository` on `items`. `add` upserts by `item_id` (`CatalogService` re-adds
    the same item on a refresh sync rather than calling a separate update method)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, item: Item) -> None:
        values = {
            "item_id": str(item.item_id),
            "sku": item.sku,
            "name": item.name,
            "owning_connection_id": str(item.owning_connection_id),
        }
        session = self._session_factory()
        try:
            stmt = pg_insert(items_table).values(**values)
            stmt = stmt.on_conflict_do_update(index_elements=["item_id"], set_=values)
            session.execute(stmt)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def find_by_sku(self, sku: str) -> Item | None:
        session = self._session_factory()
        try:
            row = session.execute(select(items_table).where(items_table.c.sku == sku)).first()
        finally:
            session.close()
        return _to_model(row) if row is not None else None

    def get(self, item_id: str) -> Item | None:
        session = self._session_factory()
        try:
            row = session.execute(select(items_table).where(items_table.c.item_id == item_id)).first()
        finally:
            session.close()
        return _to_model(row) if row is not None else None

    def list_all(self) -> list[Item]:
        session = self._session_factory()
        try:
            rows = session.execute(select(items_table)).all()
        finally:
            session.close()
        return [_to_model(row) for row in rows]
