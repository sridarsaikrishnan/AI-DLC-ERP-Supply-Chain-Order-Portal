"""In-memory connection repository (tests + simple local runs)."""

from __future__ import annotations

from src.shared.types import ConnectionId

from ..domain.models import ErpConnection


class InMemoryConnectionRepository:
    def __init__(self) -> None:
        self._by_id: dict[ConnectionId, ErpConnection] = {}

    def add(self, connection: ErpConnection) -> None:
        self._by_id[connection.connection_id] = connection

    def get(self, connection_id: ConnectionId) -> ErpConnection | None:
        return self._by_id.get(connection_id)

    def list_active(self) -> list[ErpConnection]:
        return [c for c in self._by_id.values() if c.is_active]
