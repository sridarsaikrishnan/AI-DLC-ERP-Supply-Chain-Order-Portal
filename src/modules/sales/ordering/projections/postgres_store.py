"""Postgres-backed order projection store (read side) — mirrors `OrderProjectionStore`
(the in-memory version) query-for-query, backed by `orders` + `order_status_history`
(migrations 0001 + 0002 + 0008).

Increment 5: `orders` gained party columns; the per-line fulfillment facts
(shipped/delivered/invoiced quantities + the vendor "scheduled" date) live inside the
`lines` JSONB, so recording a fulfillment/invoice/vendor-date is a read-modify-write of
that column.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, MetaData, String, Table, exists, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from src.shared.money import (
    money_from_payload,
    money_to_payload,
    tax_rate_from_payload,
    tax_rate_to_payload,
)

from ..domain.calculations import sum_money
from ..domain.models import OrderState, line_is_delivered
from .read_models import (
    OperatorOrderView,
    OrderLineView,
    Parties,
    ResellerOrderView,
    TimelineEntry,
    delivery_status,
    fulfillment_status,
    invoice_status,
    status_label,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

log = logging.getLogger(__name__)

_metadata = MetaData()

orders_table = Table(
    "orders",
    _metadata,
    Column("order_id", String, primary_key=True),
    Column("tenant_id", String, nullable=False),
    Column("client_reference", String, nullable=False),
    Column("state", String, nullable=False),
    Column("owning_connection_id", String),
    Column("erp_order_id", String),
    Column("lines", JSONB, nullable=False),
    # Increment 5 party columns (reseller-safe — no ERP identity):
    Column("quote_id", String, nullable=False, server_default=""),
    Column("operating_company_id", String, nullable=False, server_default=""),
    Column("end_customer_name", String, nullable=False, server_default=""),
    Column("ship_to", String, nullable=False, server_default=""),
)

order_status_history_table = Table(
    "order_status_history",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("order_id", String, nullable=False),
    Column("tenant_id", String, nullable=False),
    Column("state", String, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
)


def _line_to_json(line: OrderLineView) -> dict:
    return {
        "product_key": line.product_key,
        "quantity": line.quantity,
        "unit_of_measure": line.unit_of_measure,
        "line_id": line.line_id,
        "kind": line.kind,
        "unit_price": money_to_payload(line.unit_price),
        "line_total": money_to_payload(line.line_total),
        "tax_rates": [tax_rate_to_payload(t) for t in line.tax_rates],
        "line_discount": money_to_payload(line.line_discount),
        "shipped_quantity": line.shipped_quantity,
        "delivered_quantity": line.delivered_quantity,
        "invoiced_quantity": line.invoiced_quantity,
        "scheduled_date": line.scheduled_date,
    }


def _line_from_json(line: dict) -> OrderLineView:
    return OrderLineView(
        product_key=str(line["product_key"]),
        quantity=float(line["quantity"]),
        unit_of_measure=str(line["unit_of_measure"]),
        line_id=str(line.get("line_id") or line["product_key"]),
        kind=str(line.get("kind") or "PHYSICAL"),
        unit_price=money_from_payload(line.get("unit_price")),
        line_total=money_from_payload(line.get("line_total")),
        tax_rates=[tax_rate_from_payload(t) for t in (line.get("tax_rates") or [])],
        line_discount=money_from_payload(line.get("line_discount")),
        shipped_quantity=float(line.get("shipped_quantity") or 0.0),
        delivered_quantity=float(line.get("delivered_quantity") or 0.0),
        invoiced_quantity=float(line.get("invoiced_quantity") or 0.0),
        scheduled_date=line.get("scheduled_date"),
    )


class PostgresOrderProjectionStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    # --- mutations (used by the projector; redelivery-tolerant) ---
    def create(
        self,
        order_id: str,
        tenant_id: str,
        client_reference: str,
        lines: list[OrderLineView],
        parties: Parties | None = None,
    ) -> None:
        parties = parties or Parties()
        session = self._session_factory()
        try:
            stmt = (
                pg_insert(orders_table)
                .values(
                    order_id=order_id,
                    tenant_id=tenant_id,
                    client_reference=client_reference,
                    state=OrderState.SUBMITTED.value,
                    lines=[_line_to_json(line) for line in lines],
                    quote_id=parties.quote_id,
                    operating_company_id=parties.operating_company_id,
                    end_customer_name=parties.end_customer_name,
                    ship_to=parties.ship_to,
                )
                .on_conflict_do_nothing(index_elements=["order_id"])
            )
            session.execute(stmt)
            session.commit()
        except IntegrityError:
            # OrderService.place_order already calls exists() (below, in the queries
            # section) before submitting — this only fires on the narrow race the
            # docstring on DuplicateOrderReference names: two submissions with the same
            # (tenant_id, client_reference) both passed that check before either one's
            # projection existed yet. Don't retry — retrying hits the same constraint
            # forever. The order's events are safely in the event store either way;
            # only this one's projection row is skipped.
            session.rollback()
            log.warning(
                "order %s projection skipped: tenant %s already has an order with "
                "client_reference %r",
                order_id,
                tenant_id,
                client_reference,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_state(self, order_id: str, state: OrderState, occurred_at: str) -> None:
        session = self._session_factory()
        try:
            tenant_id = session.execute(
                select(orders_table.c.tenant_id).where(orders_table.c.order_id == order_id)
            ).scalar_one_or_none()
            if tenant_id is None:
                session.commit()
                return
            session.execute(
                orders_table.update()
                .where(orders_table.c.order_id == order_id)
                .values(state=state.value)
            )
            label = status_label(state)
            last_label = session.execute(
                select(order_status_history_table.c.state)
                .where(order_status_history_table.c.order_id == order_id)
                .order_by(order_status_history_table.c.id.desc())
                .limit(1)
            ).scalar_one_or_none()
            if last_label != label:
                session.execute(
                    order_status_history_table.insert().values(
                        order_id=order_id, tenant_id=tenant_id, state=label, occurred_at=occurred_at
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_owning_connection(self, order_id: str, connection_id: str) -> None:
        self._set(order_id, owning_connection_id=connection_id)

    def set_erp_order_id(self, order_id: str, erp_order_id: str) -> None:
        self._set(order_id, erp_order_id=erp_order_id)

    def _set(self, order_id: str, **values: object) -> None:
        session = self._session_factory()
        try:
            session.execute(
                orders_table.update().where(orders_table.c.order_id == order_id).values(**values)
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _mutate_line(self, order_id: str, line_id: str, mutate) -> None:
        session = self._session_factory()
        try:
            raw = session.execute(
                select(orders_table.c.lines).where(orders_table.c.order_id == order_id)
            ).scalar_one_or_none()
            if raw is None:
                session.commit()
                return
            lines = list(raw)
            for i, line in enumerate(lines):
                if str(line.get("line_id") or line.get("product_key")) == line_id:
                    lines[i] = mutate(dict(line))
                    break
            session.execute(
                orders_table.update().where(orders_table.c.order_id == order_id).values(lines=lines)
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def record_fulfillment(
        self,
        order_id: str,
        line_id: str,
        quantity: float,
        carrier: str | None,
        proof_of_delivery: str | None,
    ) -> None:
        def mutate(line: dict) -> dict:
            line["shipped_quantity"] = float(line.get("shipped_quantity") or 0.0) + quantity
            if line_is_delivered(str(line.get("kind") or "PHYSICAL"), carrier, proof_of_delivery):
                line["delivered_quantity"] = float(line.get("delivered_quantity") or 0.0) + quantity
            return line

        self._mutate_line(order_id, line_id, mutate)

    def record_invoice(self, order_id: str, line_id: str, quantity: float) -> None:
        def mutate(line: dict) -> dict:
            line["invoiced_quantity"] = float(line.get("invoiced_quantity") or 0.0) + quantity
            return line

        self._mutate_line(order_id, line_id, mutate)

    def set_scheduled_date(self, order_id: str, line_id: str, scheduled_date: str) -> None:
        def mutate(line: dict) -> dict:
            line["scheduled_date"] = scheduled_date
            return line

        self._mutate_line(order_id, line_id, mutate)

    # --- queries ---
    def exists(self, tenant_id: str, client_reference: str) -> bool:
        session = self._session_factory()
        try:
            return bool(
                session.execute(
                    select(
                        exists().where(
                            orders_table.c.tenant_id == tenant_id,
                            orders_table.c.client_reference == client_reference,
                        )
                    )
                ).scalar()
            )
        finally:
            session.close()

    @staticmethod
    def _lines(raw_lines: list[dict]) -> list[OrderLineView]:
        return [_line_from_json(line) for line in raw_lines]

    @staticmethod
    def _subtotal(lines: list[OrderLineView]):
        return sum_money([line.line_total for line in lines if line.line_total is not None])

    def _timeline(self, session: Session, order_id: str) -> list[TimelineEntry]:
        rows = session.execute(
            select(order_status_history_table.c.state, order_status_history_table.c.occurred_at)
            .where(order_status_history_table.c.order_id == order_id)
            .order_by(order_status_history_table.c.id)
        ).all()
        return [
            TimelineEntry(status=row.state, occurred_at=row.occurred_at.isoformat()) for row in rows
        ]

    @staticmethod
    def _parties(row) -> Parties:
        return Parties(
            end_customer_name=row.end_customer_name or "",
            ship_to=row.ship_to or "",
            operating_company_id=row.operating_company_id or "",
            quote_id=row.quote_id or "",
        )

    def get_reseller_view(self, tenant_id: str, order_id: str) -> ResellerOrderView | None:
        session = self._session_factory()
        try:
            row = session.execute(
                select(orders_table).where(
                    orders_table.c.order_id == order_id, orders_table.c.tenant_id == tenant_id
                )
            ).first()
            if row is None:  # tenant scoping (fail-closed): wrong tenant reads as not-found
                return None
            lines = self._lines(row.lines)
            return ResellerOrderView(
                order_id=row.order_id,
                client_reference=row.client_reference,
                status=status_label(OrderState(row.state)),
                lines=lines,
                timeline=self._timeline(session, order_id),
                subtotal=self._subtotal(lines),
                fulfillment_status=fulfillment_status(lines),
                delivery_status=delivery_status(lines),
                invoice_status=invoice_status(lines),
                parties=self._parties(row),
            )
        finally:
            session.close()

    def list_reseller_views(self, tenant_id: str) -> list[ResellerOrderView]:
        session = self._session_factory()
        try:
            rows = session.execute(
                select(orders_table).where(orders_table.c.tenant_id == tenant_id)
            ).all()
            views = []
            for row in rows:
                lines = self._lines(row.lines)
                views.append(
                    ResellerOrderView(
                        order_id=row.order_id,
                        client_reference=row.client_reference,
                        status=status_label(OrderState(row.state)),
                        lines=lines,
                        timeline=self._timeline(session, row.order_id),
                        subtotal=self._subtotal(lines),
                        fulfillment_status=fulfillment_status(lines),
                        delivery_status=delivery_status(lines),
                        invoice_status=invoice_status(lines),
                        parties=self._parties(row),
                    )
                )
            return views
        finally:
            session.close()

    def get_operator_view(self, order_id: str) -> OperatorOrderView | None:
        session = self._session_factory()
        try:
            row = session.execute(
                select(orders_table).where(orders_table.c.order_id == order_id)
            ).first()
            if row is None:
                return None
            lines = self._lines(row.lines)
            return self._operator_view(session, row, lines)
        finally:
            session.close()

    def list_operator_views(self) -> list[OperatorOrderView]:
        """Cross-tenant — operator debugging/visibility only, never reseller-reachable."""
        session = self._session_factory()
        try:
            rows = session.execute(select(orders_table)).all()
            return [self._operator_view(session, row, self._lines(row.lines)) for row in rows]
        finally:
            session.close()

    def _operator_view(
        self, session: Session, row, lines: list[OrderLineView]
    ) -> OperatorOrderView:
        return OperatorOrderView(
            order_id=row.order_id,
            tenant_id=row.tenant_id,
            client_reference=row.client_reference,
            status=status_label(OrderState(row.state)),
            owning_connection_id=row.owning_connection_id,
            erp_order_id=row.erp_order_id,
            lines=lines,
            timeline=self._timeline(session, row.order_id),
            subtotal=self._subtotal(lines),
            fulfillment_status=fulfillment_status(lines),
            delivery_status=delivery_status(lines),
            invoice_status=invoice_status(lines),
            parties=self._parties(row),
        )
