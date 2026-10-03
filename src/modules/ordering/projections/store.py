"""In-memory order projection store (read side).

Reseller reads are tenant-scoped (a reseller can only see their own orders and never
ERP identity). A Postgres-backed store implements the same query surface in Phase 2's
persistence slice.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.calculations import sum_money
from ..domain.models import OrderState
from .read_models import (
    OperatorOrderView,
    OrderLineView,
    ResellerOrderView,
    TimelineEntry,
    status_label,
)


def _subtotal(lines: list[OrderLineView]):
    return sum_money([l.line_total for l in lines if l.line_total is not None])


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


class OrderProjectionStore:
    def __init__(self) -> None:
        self._records: dict[str, _Record] = {}

    # --- mutations (used by the projector) ---
    def create(self, order_id: str, tenant_id: str, client_reference: str, lines: list[OrderLineView]) -> None:
        self._records[order_id] = _Record(
            order_id=order_id,
            tenant_id=tenant_id,
            client_reference=client_reference,
            state=OrderState.SUBMITTED,
            lines=list(lines),
        )

    def set_state(self, order_id: str, state: OrderState, occurred_at: str) -> None:
        record = self._records.get(order_id)
        if record is None:
            return
        record.state = state
        label = status_label(state)
        # Several internal states share a reseller-facing label (e.g. VALIDATED and
        # READY_FOR_DELIVERY both read "Validated") — collapse consecutive duplicates so
        # the timeline doesn't show the same status twice in a row.
        if not record.timeline or record.timeline[-1].status != label:
            record.timeline.append(TimelineEntry(status=label, occurred_at=occurred_at))

    def set_owning_connection(self, order_id: str, connection_id: str) -> None:
        if (record := self._records.get(order_id)) is not None:
            record.owning_connection_id = connection_id

    def set_erp_order_id(self, order_id: str, erp_order_id: str) -> None:
        if (record := self._records.get(order_id)) is not None:
            record.erp_order_id = erp_order_id

    # --- queries ---
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
        )
