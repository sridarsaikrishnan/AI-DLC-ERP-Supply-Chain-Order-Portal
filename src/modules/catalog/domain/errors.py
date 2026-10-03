"""Catalog domain errors."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.types import ConnectionId


class ItemOwnershipConflict(Exception):
    """Raised when a SKU synced from one connection is already owned by another."""

    def __init__(
        self, sku: str, existing_owner: ConnectionId, incoming_owner: ConnectionId
    ) -> None:
        super().__init__(
            f"SKU '{sku}' is owned by '{existing_owner}' but was synced from '{incoming_owner}'"
        )
        self.sku = sku
        self.existing_owner = existing_owner
        self.incoming_owner = incoming_owner
