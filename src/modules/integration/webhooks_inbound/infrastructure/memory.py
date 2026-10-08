"""In-memory dedup store + order locator (tests / local)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.types import ConnectionId, OrderId


class InMemoryEventInbox:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bytes]] = []

    def append(self, connection_id: str, body: bytes) -> None:
        self.rows.append((str(connection_id), body))


class InMemoryDedupStore:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def seen(self, key: str) -> bool:
        return key in self._seen

    def mark(self, key: str) -> None:
        self._seen.add(key)


class InMemoryOrderLocator:
    def __init__(self) -> None:
        self._by_ref: dict[tuple[str, str], OrderId] = {}

    def record(self, connection_id: ConnectionId, erp_order_id: str, order_id: OrderId) -> None:
        self._by_ref[(str(connection_id), erp_order_id)] = order_id

    def find_order(self, connection_id: ConnectionId, erp_order_id: str) -> OrderId | None:
        return self._by_ref.get((str(connection_id), erp_order_id))
