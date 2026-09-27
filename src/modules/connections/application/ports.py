"""Ports the connections module depends on (implemented by infrastructure)."""

from __future__ import annotations

from typing import Protocol

from src.shared.types import ConnectionId

from ..domain.models import ErpConnection


class ConnectionRepository(Protocol):
    def add(self, connection: ErpConnection) -> None: ...
    def get(self, connection_id: ConnectionId) -> ErpConnection | None: ...
    def update(self, connection: ErpConnection) -> None: ...
    def list_active(self) -> list[ErpConnection]: ...
    def list_all(self) -> list[ErpConnection]: ...
