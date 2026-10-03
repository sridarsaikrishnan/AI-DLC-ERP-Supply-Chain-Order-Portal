"""Ports the ordering application depends on (implemented by other modules' adapters).

Kept as narrow queries so ordering never imports catalog/tenancy internals directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.shared.types import ConnectionId, TenantId


class OwnershipQuery(Protocol):
    def owner_of(self, product_key: str) -> ConnectionId | None: ...


class BindingQuery(Protocol):
    def is_bound(self, tenant_id: TenantId, connection_id: ConnectionId) -> bool: ...
