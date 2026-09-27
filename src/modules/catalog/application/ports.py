"""Ports for the catalog module."""

from __future__ import annotations

from typing import Protocol

from ..domain.models import Item


class ItemRepository(Protocol):
    def add(self, item: Item) -> None: ...
    def find_by_sku(self, sku: str) -> Item | None: ...
    def get(self, item_id: str) -> Item | None: ...
