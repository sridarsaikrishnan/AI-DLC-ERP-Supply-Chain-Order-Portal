"""ReturnService — records a return (RMA). Standalone: not wired into
`Order.fulfillment_status` yet (see `Return`'s own docstring for why), so no order
repository or UnitOfWork."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.shared.types import generate_id

from ..domain.aggregate import Return

if TYPE_CHECKING:
    from src.shared.eventsourcing import EventSourcedRepository


class ReturnService:
    def __init__(self, returns: EventSourcedRepository[Return]) -> None:
        self._returns = returns

    def record(self, *, order_id: str, lines: list[dict[str, Any]], reason_code: str) -> Return:
        ret = Return.record(
            return_id=generate_id("ret"), order_id=order_id, lines=lines, reason_code=reason_code
        )
        self._returns.save(ret)
        return ret
