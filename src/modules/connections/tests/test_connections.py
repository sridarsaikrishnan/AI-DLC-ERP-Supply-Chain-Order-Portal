from __future__ import annotations

from src.modules.connections.application.service import ConnectionService
from src.modules.connections.domain.models import ConnectionStatus, ErpType
from src.modules.connections.infrastructure.memory import InMemoryConnectionRepository


def _service() -> ConnectionService:
    return ConnectionService(InMemoryConnectionRepository())


def test_register_creates_active_connection_with_prefixed_id() -> None:
    svc = _service()
    conn = svc.register(
        erp_type=ErpType.ODOO,
        instance_label="Odoo EU-1",
        base_url="http://odoo:8069",
        database="odoo",
        username="admin",
        secret_ref="arn:secret:odoo-eu1",
    )
    assert conn.connection_id.startswith("conn_")
    assert conn.status is ConnectionStatus.ACTIVE
    assert conn.is_active
    assert svc.get(conn.connection_id) is conn


def test_secret_is_a_reference_not_a_raw_credential() -> None:
    conn = _service().register(
        erp_type=ErpType.ODOO,
        instance_label="Odoo US-1",
        base_url="https://odoo-us.example",
        database="odoo_us",
        username="api",
        secret_ref="arn:secret:odoo-us1",
    )
    # secret_ref is a pointer; no plaintext password field exists on the model
    assert conn.secret_ref.startswith("arn:")
    assert not hasattr(conn, "password")
