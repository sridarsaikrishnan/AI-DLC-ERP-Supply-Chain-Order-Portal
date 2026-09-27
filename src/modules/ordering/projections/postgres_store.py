"""Postgres-backed order projection store (read side) — mirrors `OrderProjectionStore`
(the in-memory version) query-for-query, backed by `orders` + `order_status_history`
(migrations 0001 + 0002).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, DateTime, MetaData, String, Table, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from ..domain.models import OrderState
from .read_models import OperatorOrderView, OrderLineView, ResellerOrderView, TimelineEntry, status_label

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


class PostgresOrderProjectionStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    # --- mutations (used by the projector; the consumer is at-least-once so these must
    # tolerate redelivery of the same event — item C is responsible for deduping on
    # event_id via `processed_events` before calling the projector at all, but `create`
    # also no-ops on a duplicate order_id as a second line of defense) ---
    def create(
        self, order_id: str, tenant_id: str, client_reference: str, lines: list[OrderLineView]
    ) -> None:
        session = self._session_factory()
        try:
            stmt = pg_insert(orders_table).values(
                order_id=order_id,
                tenant_id=tenant_id,
                client_reference=client_reference,
                state=OrderState.SUBMITTED.value,
                lines=[
                    {
                        "product_key": line.product_key,
                        "quantity": line.quantity,
                        "unit_of_measure": line.unit_of_measure,
                    }
                    for line in lines
                ],
            ).on_conflict_do_nothing(index_elements=["order_id"])
            session.execute(stmt)
            session.commit()
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
                orders_table.update().where(orders_table.c.order_id == order_id).values(state=state.value)
            )
            label = status_label(state)
            # Several internal states share a reseller-facing label (e.g. VALIDATED and
            # READY_FOR_DELIVERY both read "Validated") — collapse consecutive duplicates
            # so the timeline doesn't show the same status twice in a row.
            last_label = session.execute(
                select(order_status_history_table.c.state)
                .where(order_status_history_table.c.order_id == order_id)
                .order_by(order_status_history_table.c.id.desc())
                .limit(1)
            ).scalar_one_or_none()
            if last_label != label:
                session.execute(
                    order_status_history_table.insert().values(
                        order_id=order_id,
                        tenant_id=tenant_id,
                        state=label,
                        occurred_at=occurred_at,
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_owning_connection(self, order_id: str, connection_id: str) -> None:
        session = self._session_factory()
        try:
            session.execute(
                orders_table.update()
                .where(orders_table.c.order_id == order_id)
                .values(owning_connection_id=connection_id)
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_erp_order_id(self, order_id: str, erp_order_id: str) -> None:
        session = self._session_factory()
        try:
            session.execute(
                orders_table.update()
                .where(orders_table.c.order_id == order_id)
                .values(erp_order_id=erp_order_id)
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # --- queries ---
    @staticmethod
    def _lines(raw_lines: list[dict[str, object]]) -> list[OrderLineView]:
        return [
            OrderLineView(
                product_key=str(line["product_key"]),
                quantity=float(line["quantity"]),  # type: ignore[arg-type]
                unit_of_measure=str(line["unit_of_measure"]),
            )
            for line in raw_lines
        ]

    def _timeline(self, session: Session, order_id: str) -> list[TimelineEntry]:
        rows = session.execute(
            select(order_status_history_table.c.state, order_status_history_table.c.occurred_at)
            .where(order_status_history_table.c.order_id == order_id)
            .order_by(order_status_history_table.c.id)
        ).all()
        return [TimelineEntry(status=row.state, occurred_at=row.occurred_at.isoformat()) for row in rows]

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
            return ResellerOrderView(
                order_id=row.order_id,
                client_reference=row.client_reference,
                status=status_label(OrderState(row.state)),
                lines=self._lines(row.lines),
                timeline=self._timeline(session, order_id),
            )
        finally:
            session.close()

    def list_reseller_views(self, tenant_id: str) -> list[ResellerOrderView]:
        session = self._session_factory()
        try:
            rows = session.execute(select(orders_table).where(orders_table.c.tenant_id == tenant_id)).all()
            return [
                ResellerOrderView(
                    order_id=row.order_id,
                    client_reference=row.client_reference,
                    status=status_label(OrderState(row.state)),
                    lines=self._lines(row.lines),
                    timeline=self._timeline(session, row.order_id),
                )
                for row in rows
            ]
        finally:
            session.close()

    def get_operator_view(self, order_id: str) -> OperatorOrderView | None:
        session = self._session_factory()
        try:
            row = session.execute(select(orders_table).where(orders_table.c.order_id == order_id)).first()
            if row is None:
                return None
            return OperatorOrderView(
                order_id=row.order_id,
                tenant_id=row.tenant_id,
                client_reference=row.client_reference,
                status=status_label(OrderState(row.state)),
                owning_connection_id=row.owning_connection_id,
                erp_order_id=row.erp_order_id,
                lines=self._lines(row.lines),
                timeline=self._timeline(session, order_id),
            )
        finally:
            session.close()

    def list_operator_views(self) -> list[OperatorOrderView]:
        """Cross-tenant — operator debugging/visibility only, never reseller-reachable."""
        session = self._session_factory()
        try:
            rows = session.execute(select(orders_table)).all()
            return [
                OperatorOrderView(
                    order_id=row.order_id,
                    tenant_id=row.tenant_id,
                    client_reference=row.client_reference,
                    status=status_label(OrderState(row.state)),
                    owning_connection_id=row.owning_connection_id,
                    erp_order_id=row.erp_order_id,
                    lines=self._lines(row.lines),
                    timeline=self._timeline(session, row.order_id),
                )
                for row in rows
            ]
        finally:
            session.close()
