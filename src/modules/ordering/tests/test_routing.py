from __future__ import annotations

from src.modules.ordering.domain.routing import (
    RejectionReason,
    resolve_owning_connection,
)
from src.shared.types import ConnectionId

# ownership fixture: which connection owns each product
_OWNERS: dict[str, ConnectionId] = {
    "ANVIL": ConnectionId("conn_1"),
    "SPRING": ConnectionId("conn_1"),
    "ROCKET": ConnectionId("conn_2"),
}


def _owner_of(product_key: str) -> ConnectionId | None:
    return _OWNERS.get(product_key)


def _bound_to(*connections: str):
    allowed = {ConnectionId(c) for c in connections}
    return lambda c: c in allowed


def test_single_owner_and_bound_routes() -> None:
    decision = resolve_owning_connection(["ANVIL", "SPRING"], _owner_of, _bound_to("conn_1"))
    assert decision.routed
    assert decision.connection_id == ConnectionId("conn_1")


def test_mixed_erp_is_rejected() -> None:
    decision = resolve_owning_connection(["ANVIL", "ROCKET"], _owner_of, _bound_to("conn_1", "conn_2"))
    assert not decision.routed
    assert decision.reason is RejectionReason.MIXED_ERP


def test_unknown_item_is_rejected() -> None:
    decision = resolve_owning_connection(["ANVIL", "MYSTERY"], _owner_of, _bound_to("conn_1"))
    assert not decision.routed
    assert decision.reason is RejectionReason.UNKNOWN_ITEM


def test_no_binding_is_rejected() -> None:
    decision = resolve_owning_connection(["ROCKET"], _owner_of, _bound_to("conn_1"))
    assert not decision.routed
    assert decision.reason is RejectionReason.NO_BINDING


def test_empty_order_is_rejected() -> None:
    decision = resolve_owning_connection([], _owner_of, _bound_to("conn_1"))
    assert not decision.routed
    assert decision.reason is RejectionReason.EMPTY_ORDER
