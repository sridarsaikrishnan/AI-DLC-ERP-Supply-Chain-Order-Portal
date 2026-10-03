"""Property-based tests for ownership routing (Hypothesis).

Properties (hold for all generated inputs):
- the function is total — it always returns a RoutingDecision, never raises;
- a single distinct owner + a verified binding => routed to that owner;
- items spanning >1 owner => MIXED_ERP;
- any unknown item => UNKNOWN_ITEM (precedence over mixed).
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from src.modules.ordering.domain.routing import (
    RejectionReason,
    RoutingDecision,
    resolve_owning_connection,
)
from src.shared.types import ConnectionId

product_keys = st.lists(st.sampled_from(["A", "B", "C", "UNKNOWN"]), max_size=6)


def _owner_of(product_key: str) -> ConnectionId | None:
    mapping = {"A": "conn_1", "B": "conn_1", "C": "conn_2"}
    value = mapping.get(product_key)
    return ConnectionId(value) if value else None


@given(keys=product_keys, bound_all=st.booleans())
def test_routing_is_total(keys: list[str], bound_all: bool) -> None:
    decision = resolve_owning_connection(keys, owner_of=_owner_of, is_bound=lambda _c: bound_all)
    assert isinstance(decision, RoutingDecision)
    if decision.routed:
        assert decision.connection_id is not None
    else:
        assert decision.reason in set(RejectionReason)


@given(keys=st.lists(st.sampled_from(["A", "B"]), min_size=1, max_size=5))
def test_single_owner_bound_always_routes(keys: list[str]) -> None:
    decision = resolve_owning_connection(keys, owner_of=_owner_of, is_bound=lambda _c: True)
    assert decision.routed
    assert decision.connection_id == ConnectionId("conn_1")


@given(
    keys=st.lists(st.sampled_from(["A", "C"]), min_size=2, max_size=6).filter(
        lambda ks: "A" in ks and "C" in ks
    )
)
def test_mixed_owners_rejected(keys: list[str]) -> None:
    decision = resolve_owning_connection(keys, owner_of=_owner_of, is_bound=lambda _c: True)
    assert not decision.routed
    assert decision.reason is RejectionReason.MIXED_ERP


@given(
    keys=st.lists(st.sampled_from(["A", "UNKNOWN"]), min_size=1, max_size=6).filter(
        lambda ks: "UNKNOWN" in ks
    )
)
def test_unknown_item_rejected(keys: list[str]) -> None:
    decision = resolve_owning_connection(keys, owner_of=_owner_of, is_bound=lambda _c: True)
    assert not decision.routed
    assert decision.reason is RejectionReason.UNKNOWN_ITEM
