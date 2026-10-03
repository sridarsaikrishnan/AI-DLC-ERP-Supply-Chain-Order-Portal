"""Catalog domain model + pure ownership rules."""

from __future__ import annotations

from dataclasses import dataclass

from src.shared.money import Money
from src.shared.types import ConnectionId, ItemId


@dataclass
class Item:
    item_id: ItemId
    sku: str
    name: str
    owning_connection_id: ConnectionId
    unit_price: Money | None = None


def detect_ownership_conflict(
    existing_owner: ConnectionId | None, incoming_owner: ConnectionId
) -> bool:
    """True when the same SKU is being claimed by a different connection than its current owner."""
    return existing_owner is not None and existing_owner != incoming_owner
