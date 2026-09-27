"""CatalogService — sync items from a connection, enforcing single ownership."""

from __future__ import annotations

from src.shared.types import ConnectionId, ItemId, generate_id

from ..domain.errors import ItemOwnershipConflict
from ..domain.models import Item, detect_ownership_conflict
from .ports import ItemRepository


class CatalogService:
    def __init__(self, repository: ItemRepository) -> None:
        self._repository = repository

    def sync_item(self, *, sku: str, name: str, owning_connection_id: ConnectionId) -> Item:
        """Register or refresh an item. Raises if a different connection already owns the SKU."""
        existing = self._repository.find_by_sku(sku)
        existing_owner = existing.owning_connection_id if existing else None
        if detect_ownership_conflict(existing_owner, owning_connection_id):
            assert existing_owner is not None
            raise ItemOwnershipConflict(sku, existing_owner, owning_connection_id)

        if existing is not None:
            existing.name = name
            self._repository.add(existing)
            return existing

        item = Item(
            item_id=ItemId(generate_id("item")),
            sku=sku,
            name=name,
            owning_connection_id=owning_connection_id,
        )
        self._repository.add(item)
        return item
