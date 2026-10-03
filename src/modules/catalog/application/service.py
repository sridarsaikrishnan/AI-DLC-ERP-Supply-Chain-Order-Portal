"""CatalogService — sync items from a connection, enforcing single ownership."""

from __future__ import annotations

from src.shared.messaging.facts import FactPublisher, make_fact
from src.shared.types import ConnectionId, ItemId, generate_id

from ..domain.errors import ItemOwnershipConflict
from ..domain.events import ITEM_SYNCED
from ..domain.models import Item, ItemKind, detect_ownership_conflict
from .ports import ItemRepository


class CatalogService:
    def __init__(self, repository: ItemRepository, facts: FactPublisher) -> None:
        self._repository = repository
        self._facts = facts

    def sync_item(
        self,
        *,
        sku: str,
        name: str,
        owning_connection_id: ConnectionId,
        kind: ItemKind = ItemKind.PHYSICAL,
    ) -> Item:
        """Register or refresh an item. Raises if a different connection already owns the SKU.

        No price/tax/discount here anymore (Increment 5, FR-B4 / ADR-0016) — the catalog
        says only what the product is; price lives on the Quote."""
        existing = self._repository.find_by_sku(sku)
        existing_owner = existing.owning_connection_id if existing else None
        if detect_ownership_conflict(existing_owner, owning_connection_id):
            assert existing_owner is not None
            raise ItemOwnershipConflict(sku, existing_owner, owning_connection_id)

        if existing is not None:
            existing.name = name
            existing.kind = kind
            self._repository.add(existing)
            self._publish(existing)
            return existing

        item = Item(
            item_id=ItemId(generate_id("item")),
            sku=sku,
            name=name,
            owning_connection_id=owning_connection_id,
            kind=kind,
        )
        self._repository.add(item)
        self._publish(item)
        return item

    def _publish(self, item: Item) -> None:
        self._facts.publish(
            make_fact(
                stream_id=str(item.item_id),
                aggregate_type="Item",
                event_type=ITEM_SYNCED,
                payload={
                    "item_id": str(item.item_id),
                    "sku": item.sku,
                    "name": item.name,
                    "owning_connection_id": str(item.owning_connection_id),
                    "kind": item.kind.value,
                },
            )
        )
