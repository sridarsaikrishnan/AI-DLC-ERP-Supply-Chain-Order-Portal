"""Return aggregate — a minimal, record-only event-sourced aggregate (an RMA: goods sent
back). Split out of `fulfillment`.

Standalone record — not yet wired into `Order.fulfillment_status` (reversing
`fulfilled_qty_by_line`). Deliberately scoped out: whether a return should reopen
fulfillment status is a real business-policy question, not answered here.
"""

from __future__ import annotations

from typing import Any

from src.shared.eventsourcing import Aggregate

from .events import ReturnRecorded


class Return(Aggregate):
    aggregate_type = "Return"

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.order_id: str = ""
        self.lines: list[dict[str, Any]] = []
        self.reason_code: str = ""

    @classmethod
    def record(
        cls, *, return_id: str, order_id: str, lines: list[dict[str, Any]], reason_code: str
    ) -> Return:
        if not lines:
            raise ValueError("a return must have at least one line")
        r = cls(return_id)
        r.emit(
            ReturnRecorded(
                return_id=return_id, order_id=order_id, lines=lines, reason_code=reason_code
            )
        )
        return r

    def _apply_ReturnRecorded(self, e: ReturnRecorded) -> None:
        self.order_id = e.order_id
        self.lines = list(e.lines)
        self.reason_code = e.reason_code

    def snapshot_state(self) -> dict[str, Any]:
        return {"order_id": self.order_id, "lines": self.lines, "reason_code": self.reason_code}

    def restore(self, state: dict[str, Any]) -> None:
        self.order_id = state["order_id"]
        self.lines = state["lines"]
        self.reason_code = state["reason_code"]
