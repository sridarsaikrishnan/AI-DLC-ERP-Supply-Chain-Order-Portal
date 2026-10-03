"""Ports for inbound webhook processing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.modules.integration.erp.domain.status_mapping import CanonicalStatus
    from src.shared.types import ConnectionId, OrderId


class SecretResolver(Protocol):
    def secret_for(self, connection_id: ConnectionId) -> str | None: ...


class DedupStore(Protocol):
    def seen(self, key: str) -> bool: ...
    def mark(self, key: str) -> None: ...


class OrderLocator(Protocol):
    """Reverse routing: (connection, erp_order_id) -> our order id, or None."""

    def find_order(self, connection_id: ConnectionId, erp_order_id: str) -> OrderId | None: ...


class OrderStatusPort(Protocol):
    def apply_status(self, order_id: OrderId, status: CanonicalStatus) -> None: ...
