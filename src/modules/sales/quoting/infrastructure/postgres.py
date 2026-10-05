"""Postgres-backed quoting repositories — `subsidiaries` and `quotes`.

Quote lines live in a JSONB column on `quotes` (same pattern as `orders.lines`), not a
separate table — a quote's lines are only ever read as a whole with the quote.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, Date, MetaData, String, Table, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.shared.money import (
    money_from_payload,
    money_to_payload,
    tax_rate_from_payload,
    tax_rate_to_payload,
)
from src.shared.types import TenantId

from ..domain.models import (
    EndCustomer,
    Quote,
    QuoteLine,
    QuoteStatus,
    Subsidiary,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Row
    from sqlalchemy.orm import Session, sessionmaker

_metadata = MetaData()

subsidiaries_table = Table(
    "subsidiaries",
    _metadata,
    Column("subsidiary_id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("country", String, nullable=False),
    Column("language", String, nullable=False),
)

subsidiary_routes_table = Table(
    "subsidiary_routes",
    _metadata,
    Column("subsidiary_id", String, primary_key=True),
    Column("connection_id", String, nullable=False),
)

quotes_table = Table(
    "quotes",
    _metadata,
    Column("quote_id", String, primary_key=True),
    Column("tenant_id", String, nullable=False),
    Column("subsidiary_id", String, nullable=False),
    Column("end_customer_name", String, nullable=False),
    Column("ship_to", String, nullable=False),
    Column("currency", String, nullable=False),
    Column("valid_from", Date, nullable=False),
    Column("valid_until", Date, nullable=False),
    Column("routed_to_connection_id", String, nullable=False),
    Column("status", String, nullable=False),
    Column("lines", JSONB, nullable=False),
)


def _line_to_payload(line: QuoteLine) -> dict[str, Any]:
    return {
        "product_key": line.product_key,
        "unit_price": money_to_payload(line.unit_price),
        "unit_of_measure": line.unit_of_measure,
        "tax_rate": tax_rate_to_payload(line.tax_rate) if line.tax_rate else None,
        "line_discount": money_to_payload(line.line_discount),
        "name": line.name,
        "kind": line.kind,
    }


def _line_from_payload(data: dict[str, Any]) -> QuoteLine:
    unit_price = money_from_payload(data["unit_price"])
    assert unit_price is not None  # quote lines are always priced
    return QuoteLine(
        product_key=data["product_key"],
        unit_price=unit_price,
        unit_of_measure=data.get("unit_of_measure", ""),
        tax_rate=tax_rate_from_payload(data["tax_rate"]) if data.get("tax_rate") else None,
        line_discount=money_from_payload(data.get("line_discount")),
        name=data.get("name", ""),
        kind=data.get("kind", "PHYSICAL"),
    )


def _to_quote(row: Row) -> Quote:
    return Quote(
        quote_id=row.quote_id,
        tenant_id=TenantId(row.tenant_id),
        subsidiary_id=row.subsidiary_id,
        end_customer=EndCustomer(name=row.end_customer_name, ship_to=row.ship_to),
        currency=row.currency,
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        routed_to_connection_id=row.routed_to_connection_id,
        lines=[_line_from_payload(line) for line in row.lines],
        status=QuoteStatus(row.status),
    )


class PostgresQuoteRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def _values(self, quote: Quote) -> dict[str, Any]:
        return {
            "quote_id": quote.quote_id,
            "tenant_id": str(quote.tenant_id),
            "subsidiary_id": quote.subsidiary_id,
            "end_customer_name": quote.end_customer.name,
            "ship_to": quote.end_customer.ship_to,
            "currency": quote.currency,
            "valid_from": quote.valid_from,
            "valid_until": quote.valid_until,
            "routed_to_connection_id": quote.routed_to_connection_id,
            "status": quote.status.value,
            "lines": [_line_to_payload(line) for line in quote.lines],
        }

    def add(self, quote: Quote) -> None:
        values = self._values(quote)
        session = self._session_factory()
        try:
            stmt = pg_insert(quotes_table).values(**values)
            stmt = stmt.on_conflict_do_update(index_elements=["quote_id"], set_=values)
            session.execute(stmt)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, quote: Quote) -> None:
        self.add(quote)

    def get(self, quote_id: str) -> Quote | None:
        session = self._session_factory()
        try:
            row = session.execute(
                select(quotes_table).where(quotes_table.c.quote_id == quote_id)
            ).first()
        finally:
            session.close()
        return _to_quote(row) if row is not None else None

    def list_by_tenant(self, tenant_id: TenantId) -> list[Quote]:
        session = self._session_factory()
        try:
            rows = session.execute(
                select(quotes_table).where(quotes_table.c.tenant_id == str(tenant_id))
            ).all()
        finally:
            session.close()
        return [_to_quote(row) for row in rows]

    def list_all(self) -> list[Quote]:
        session = self._session_factory()
        try:
            rows = session.execute(select(quotes_table)).all()
        finally:
            session.close()
        return [_to_quote(row) for row in rows]


def _to_company(row: Row) -> Subsidiary:
    return Subsidiary(
        subsidiary_id=row.subsidiary_id,
        name=row.name,
        country=row.country,
        language=row.language,
    )


class PostgresSubsidiaryRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, company: Subsidiary) -> None:
        values = {
            "subsidiary_id": company.subsidiary_id,
            "name": company.name,
            "country": company.country,
            "language": company.language,
        }
        session = self._session_factory()
        try:
            stmt = pg_insert(subsidiaries_table).values(**values)
            stmt = stmt.on_conflict_do_update(index_elements=["subsidiary_id"], set_=values)
            session.execute(stmt)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, subsidiary_id: str) -> Subsidiary | None:
        session = self._session_factory()
        try:
            row = session.execute(
                select(subsidiaries_table).where(
                    subsidiaries_table.c.subsidiary_id == subsidiary_id
                )
            ).first()
        finally:
            session.close()
        return _to_company(row) if row is not None else None

    def list_all(self) -> list[Subsidiary]:
        session = self._session_factory()
        try:
            rows = session.execute(select(subsidiaries_table)).all()
        finally:
            session.close()
        return [_to_company(row) for row in rows]


class PostgresSubsidiaryRouteRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def set_route(self, subsidiary_id: str, connection_id: str) -> None:
        values = {"subsidiary_id": subsidiary_id, "connection_id": connection_id}
        session = self._session_factory()
        try:
            stmt = pg_insert(subsidiary_routes_table).values(**values)
            stmt = stmt.on_conflict_do_update(index_elements=["subsidiary_id"], set_=values)
            session.execute(stmt)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_route(self, subsidiary_id: str) -> str | None:
        session = self._session_factory()
        try:
            row = session.execute(
                select(subsidiary_routes_table).where(
                    subsidiary_routes_table.c.subsidiary_id == subsidiary_id
                )
            ).first()
        finally:
            session.close()
        return row.connection_id if row is not None else None
