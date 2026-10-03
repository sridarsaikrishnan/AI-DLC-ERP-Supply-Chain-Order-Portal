"""Catalog domain model + pure ownership rules.

The catalog answers only "what the product is" — identity, name, owning connection, and
whether it is a physical good or a license (Increment 5, FR-B4). Pricing left the catalog
in Increment 5: price/tax/discount now live on the Quote (ADR-0016, superseding ADR-0011
and ADR-0013), because a price only means something inside a quote to a specific reseller
for a bounded time, not as a standing catalog attribute.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.shared.types import ConnectionId, ItemId


class ItemKind(str, Enum):
    """Physical goods ("a box") vs. licenses (Increment 5, FR-D1). Drives the delivered
    fact (FR-D2): a box is delivered only once a carrier or proof-of-delivery is recorded;
    a license is delivered the moment it ships."""

    PHYSICAL = "PHYSICAL"
    LICENSE = "LICENSE"


@dataclass
class Item:
    item_id: ItemId
    sku: str
    name: str
    owning_connection_id: ConnectionId
    kind: ItemKind = ItemKind.PHYSICAL


def detect_ownership_conflict(
    existing_owner: ConnectionId | None, incoming_owner: ConnectionId
) -> bool:
    """True when the same SKU is being claimed by a different connection than its current owner."""
    return existing_owner is not None and existing_owner != incoming_owner
