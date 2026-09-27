"""Ports for the tenancy module."""

from __future__ import annotations

from typing import Protocol

from src.shared.types import BindingId, ConnectionId, TenantId

from ..domain.models import TenantConnectionBinding


class BindingRepository(Protocol):
    def add(self, binding: TenantConnectionBinding) -> None: ...
    def get(self, binding_id: BindingId) -> TenantConnectionBinding | None: ...
    def update(self, binding: TenantConnectionBinding) -> None: ...
    def find_by_tenant_and_connection(
        self, tenant_id: TenantId, connection_id: ConnectionId
    ) -> TenantConnectionBinding | None: ...
    def find_by_connection_and_customer(
        self, connection_id: ConnectionId, erp_customer_id: str
    ) -> TenantConnectionBinding | None: ...
