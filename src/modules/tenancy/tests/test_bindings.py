from __future__ import annotations

import pytest

from src.modules.tenancy.application.service import BindingService
from src.modules.tenancy.domain.attribution import resolve_tenant_for_customer
from src.modules.tenancy.domain.errors import BindingConflict, BindingNotFound
from src.modules.tenancy.infrastructure.memory import InMemoryBindingRepository
from src.shared.types import BindingId, ConnectionId, TenantId


def _service() -> BindingService:
    return BindingService(InMemoryBindingRepository())


def test_create_then_verify_binding() -> None:
    svc = _service()
    b = svc.create_binding(
        tenant_id=TenantId("tnt_a"), connection_id=ConnectionId("conn_1"), erp_customer_id="C-1"
    )
    assert b.binding_id.startswith("bind_")
    assert not b.is_verified
    verified = svc.verify_binding(b.binding_id)
    assert verified.is_verified


def test_reseller_cannot_bind_same_connection_twice() -> None:
    svc = _service()
    svc.create_binding(tenant_id=TenantId("tnt_a"), connection_id=ConnectionId("conn_1"), erp_customer_id="C-1")
    with pytest.raises(BindingConflict):
        svc.create_binding(tenant_id=TenantId("tnt_a"), connection_id=ConnectionId("conn_1"), erp_customer_id="C-2")


def test_erp_customer_cannot_map_to_two_tenants() -> None:
    svc = _service()
    svc.create_binding(tenant_id=TenantId("tnt_a"), connection_id=ConnectionId("conn_1"), erp_customer_id="C-1")
    with pytest.raises(BindingConflict):
        svc.create_binding(tenant_id=TenantId("tnt_b"), connection_id=ConnectionId("conn_1"), erp_customer_id="C-1")


def test_verify_missing_binding_raises() -> None:
    with pytest.raises(BindingNotFound):
        _service().verify_binding(BindingId("bind_missing"))


def test_attribution_only_through_verified_binding() -> None:
    svc = _service()
    b = svc.create_binding(tenant_id=TenantId("tnt_a"), connection_id=ConnectionId("conn_1"), erp_customer_id="C-1")
    assert resolve_tenant_for_customer(b) is None  # not verified yet -> not attributable
    svc.verify_binding(b.binding_id)
    assert resolve_tenant_for_customer(b) == TenantId("tnt_a")
    assert resolve_tenant_for_customer(None) is None
