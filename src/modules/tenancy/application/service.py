"""BindingService — create and verify tenant↔connection bindings (operator-facing).

Enforces the two uniqueness rules that guarantee cross-tenant isolation:
  - a reseller has at most one binding per connection
  - an ERP customer maps to at most one reseller
"""

from __future__ import annotations

from src.shared.types import BindingId, ConnectionId, TenantId, generate_id

from ..domain.errors import BindingConflict, BindingNotFound
from ..domain.models import BindingStatus, TenantConnectionBinding
from .ports import BindingRepository


class BindingService:
    def __init__(self, repository: BindingRepository) -> None:
        self._repository = repository

    def create_binding(
        self, *, tenant_id: TenantId, connection_id: ConnectionId, erp_customer_id: str
    ) -> TenantConnectionBinding:
        if self._repository.find_by_tenant_and_connection(tenant_id, connection_id) is not None:
            raise BindingConflict(
                f"tenant '{tenant_id}' already has a binding to connection '{connection_id}'"
            )
        if self._repository.find_by_connection_and_customer(connection_id, erp_customer_id) is not None:
            raise BindingConflict(
                f"customer '{erp_customer_id}' in connection '{connection_id}' is already bound to a tenant"
            )
        binding = TenantConnectionBinding(
            binding_id=BindingId(generate_id("bind")),
            tenant_id=tenant_id,
            connection_id=connection_id,
            erp_customer_id=erp_customer_id,
            status=BindingStatus.TO_VERIFY,
        )
        self._repository.add(binding)
        return binding

    def verify_binding(self, binding_id: BindingId) -> TenantConnectionBinding:
        binding = self._repository.get(binding_id)
        if binding is None:
            raise BindingNotFound(str(binding_id))
        binding.status = BindingStatus.VERIFIED
        self._repository.update(binding)
        return binding
