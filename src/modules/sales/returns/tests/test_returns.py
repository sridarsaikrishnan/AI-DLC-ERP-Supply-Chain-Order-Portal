from __future__ import annotations

from src.modules.sales.returns.application.service import ReturnService
from src.modules.sales.returns.domain.aggregate import Return
from src.shared.eventsourcing import EventSourcedRepository, InMemoryEventStore


def test_return_records_and_replays() -> None:
    store = InMemoryEventStore()
    repo: EventSourcedRepository[Return] = EventSourcedRepository(store, Return)
    r = Return.record(
        return_id="ret_1",
        order_id="ord_1",
        lines=[{"product_key": "ANVIL", "quantity": "2"}],
        reason_code="DAMAGED",
    )
    repo.save(r)
    assert repo.get("ret_1").reason_code == "DAMAGED"


def test_return_service_records_without_touching_order() -> None:
    return_repo: EventSourcedRepository[Return] = EventSourcedRepository(
        InMemoryEventStore(), Return
    )
    service = ReturnService(return_repo)
    ret = service.record(
        order_id="ord_1",
        lines=[{"product_key": "ANVIL", "quantity": "1"}],
        reason_code="WRONG_ITEM",
    )
    assert ret.order_id == "ord_1"
