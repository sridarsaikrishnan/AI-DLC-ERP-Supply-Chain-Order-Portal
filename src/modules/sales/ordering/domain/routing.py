"""Ownership-based routing (pure).

An order routes to exactly one ERP connection, derived from the ownership of its line
items. This is a pure function of its inputs (no I/O) so it is trivially testable and a
property-based-testing target.

Rules (supersede the earlier content-rule routing):
- every line's item must resolve to an owning connection (else reject: unknown_item)
- all lines must resolve to the SAME connection (else reject: mixed_erp)
- the tenant must hold a VERIFIED binding to that connection (else reject: no_binding)
The resolved connection is then persisted on the order and never re-derived.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from src.shared.types import ConnectionId


class RejectionReason(str, Enum):
    EMPTY_ORDER = "empty_order"
    UNKNOWN_ITEM = "unknown_item"
    MIXED_ERP = "mixed_erp"
    NO_BINDING = "no_binding"


@dataclass(frozen=True)
class RoutingDecision:
    routed: bool
    connection_id: ConnectionId | None = None
    reason: RejectionReason | None = None
    message: str | None = None

    @staticmethod
    def to(connection_id: ConnectionId) -> RoutingDecision:
        return RoutingDecision(routed=True, connection_id=connection_id)

    @staticmethod
    def reject(reason: RejectionReason, message: str) -> RoutingDecision:
        return RoutingDecision(routed=False, reason=reason, message=message)


# owner_of: product_key -> owning ConnectionId (or None if unknown/unowned)
OwnerLookup = Callable[[str], ConnectionId | None]
# is_bound: does the ordering tenant hold a VERIFIED binding to this connection?
BindingCheck = Callable[[ConnectionId], bool]


def resolve_owning_connection(
    product_keys: list[str], owner_of: OwnerLookup, is_bound: BindingCheck
) -> RoutingDecision:
    if not product_keys:
        return RoutingDecision.reject(RejectionReason.EMPTY_ORDER, "order has no line items")

    owners: set[ConnectionId] = set()
    for product_key in product_keys:
        owner = owner_of(product_key)
        if owner is None:
            return RoutingDecision.reject(
                RejectionReason.UNKNOWN_ITEM, f"item '{product_key}' has no owning connection"
            )
        owners.add(owner)

    if len(owners) > 1:
        return RoutingDecision.reject(
            RejectionReason.MIXED_ERP, "order items span multiple ERP connections"
        )

    (connection_id,) = tuple(owners)
    if not is_bound(connection_id):
        return RoutingDecision.reject(
            RejectionReason.NO_BINDING, "no verified binding to the target connection"
        )
    return RoutingDecision.to(connection_id)
