"""In-memory item repository."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.models import Item


class InMemoryItemRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Item] = {}
        self._by_sku: dict[str, Item] = {}

    def add(self, item: Item) -> None:
        self._by_id[item.item_id] = item
        self._by_sku[item.sku] = item

    def find_by_sku(self, sku: str) -> Item | None:
        return self._by_sku.get(sku)

    def get(self, item_id: str) -> Item | None:
        return self._by_id.get(item_id)

    def list_all(self) -> list[Item]:
        return list(self._by_id.values())
