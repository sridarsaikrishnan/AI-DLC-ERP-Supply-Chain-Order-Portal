"""In-memory order projection store (read side).

Reseller reads are tenant-scoped (a reseller can only see their own orders and never
ERP identity). A Postgres-backed store implements the same query surface in Phase 2's
persistence slice.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

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


def _subtotal(lines: list[OrderLineView]):
    return sum_money([line.line_total for line in lines if line.line_total is not None])


@dataclass
class _Record:
    order_id: str
    tenant_id: str
    client_reference: str
    state: OrderState
    lines: list[OrderLineView] = field(default_factory=list)
    owning_connection_id: str | None = None
    erp_order_id: str | None = None
    timeline: list[TimelineEntry] = field(default_factory=list)
    parties: Parties = field(default_factory=Parties)


class OrderProjectionStore:
    def __init__(self) -> None:
        self._records: dict[str, _Record] = {}

    # --- mutations (used by the projector) ---
    def create(
        self,
        order_id: str,
        tenant_id: str,
        client_reference: str,
        lines: list[OrderLineView],
        parties: Parties | None = None,
    ) -> None:
        self._records[order_id] = _Record(
            order_id=order_id,
            tenant_id=tenant_id,
            client_reference=client_reference,
            state=OrderState.SUBMITTED,
            lines=list(lines),
            parties=parties or Parties(),
        )

    def set_state(self, order_id: str, state: OrderState, occurred_at: str) -> None:
        record = self._records.get(order_id)
        if record is None:
            return
        record.state = state
        label = status_label(state)
        # Several internal states share a reseller-facing label (e.g. VALIDATED and
        # ACCEPTED both read "VALIDATED") — collapse consecutive duplicates so the
        # timeline doesn't show the same status twice in a row.
        if not record.timeline or record.timeline[-1].status != label:
            record.timeline.append(TimelineEntry(status=label, occurred_at=occurred_at))

    def set_owning_connection(self, order_id: str, connection_id: str) -> None:
        if (record := self._records.get(order_id)) is not None:
            record.owning_connection_id = connection_id

    def set_erp_order_id(self, order_id: str, erp_order_id: str) -> None:
        if (record := self._records.get(order_id)) is not None:
            record.erp_order_id = erp_order_id

    def _update_line(self, order_id: str, line_id: str, **changes: object) -> None:
        record = self._records.get(order_id)
        if record is None:
            return
        for i, line in enumerate(record.lines):
            if line.line_id == line_id:
                record.lines[i] = dataclasses.replace(line, **changes)
                return

    def record_fulfillment(
        self,
        order_id: str,
        line_id: str,
        quantity: float,
        carrier: str | None,
        proof_of_delivery: str | None,
    ) -> None:
        record = self._records.get(order_id)
        if record is None:
            return
        for line in record.lines:
            if line.line_id == line_id:
                delivered_delta = (
                    quantity if line_is_delivered(line.kind, carrier, proof_of_delivery) else 0.0
                )
                self._update_line(
                    order_id,
                    line_id,
                    shipped_quantity=line.shipped_quantity + quantity,
                    delivered_quantity=line.delivered_quantity + delivered_delta,
                )
                return

    def record_invoice(self, order_id: str, line_id: str, invoiced_delta: float) -> None:
        record = self._records.get(order_id)
        if record is None:
            return
        for line in record.lines:
            if line.line_id == line_id:
                self._update_line(
                    order_id, line_id, invoiced_quantity=line.invoiced_quantity + invoiced_delta
                )
                return

    def set_scheduled_date(self, order_id: str, line_id: str, scheduled_date: str) -> None:
        self._update_line(order_id, line_id, scheduled_date=scheduled_date)

    # --- queries ---
    def exists(self, tenant_id: str, client_reference: str) -> bool:
        return any(
            r.tenant_id == tenant_id and r.client_reference == client_reference
            for r in self._records.values()
        )

    def get_reseller_view(self, tenant_id: str, order_id: str) -> ResellerOrderView | None:
        record = self._records.get(order_id)
        if record is None or record.tenant_id != tenant_id:  # tenant scoping (fail-closed)
            return None
        return ResellerOrderView(
            order_id=record.order_id,
            client_reference=record.client_reference,
            status=status_label(record.state),
            lines=list(record.lines),
            timeline=list(record.timeline),
            subtotal=_subtotal(record.lines),
            fulfillment_status=fulfillment_status(record.lines),
            delivery_status=delivery_status(record.lines),
            invoice_status=invoice_status(record.lines),
            parties=record.parties,
        )

    def list_reseller_views(self, tenant_id: str) -> list[ResellerOrderView]:
        return [
            self.get_reseller_view(tenant_id, r.order_id)  # type: ignore[misc]
            for r in self._records.values()
            if r.tenant_id == tenant_id
        ]

    def list_operator_views(self) -> list[OperatorOrderView]:
        """Cross-tenant — operator debugging/visibility only, never reseller-reachable."""
        return [self.get_operator_view(r.order_id) for r in self._records.values()]  # type: ignore[misc]

    def get_operator_view(self, order_id: str) -> OperatorOrderView | None:
        record = self._records.get(order_id)
        if record is None:
            return None
        return OperatorOrderView(
            order_id=record.order_id,
            tenant_id=record.tenant_id,
            client_reference=record.client_reference,
            status=status_label(record.state),
            owning_connection_id=record.owning_connection_id,
            erp_order_id=record.erp_order_id,
            lines=list(record.lines),
            timeline=list(record.timeline),
            subtotal=_subtotal(record.lines),
            fulfillment_status=fulfillment_status(record.lines),
            delivery_status=delivery_status(record.lines),
            invoice_status=invoice_status(record.lines),
            parties=record.parties,
        )
