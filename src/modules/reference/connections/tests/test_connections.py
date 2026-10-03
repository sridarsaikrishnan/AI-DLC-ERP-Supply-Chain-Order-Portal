from __future__ import annotations

from src.modules.reference.connections.application.service import ConnectionService
from src.modules.reference.connections.domain.events import (
    CONNECTION_PAUSED,
    CONNECTION_REGISTERED,
    CONNECTION_RESUMED,
)
from src.modules.reference.connections.domain.models import ConnectionStatus, ErpType
from src.modules.reference.connections.infrastructure.memory import InMemoryConnectionRepository
from src.shared.messaging.facts import CollectingFactPublisher


def _service() -> ConnectionService:
    return ConnectionService(InMemoryConnectionRepository(), CollectingFactPublisher())


def test_register_creates_active_connection_with_prefixed_id() -> None:
    svc = _service()
    conn = svc.register(
        erp_type=ErpType.ODOO,
        instance_label="Odoo EU-1",
        base_url="http://odoo:8069",
        credentials={"database": "odoo", "username": "admin"},
        secret_ref="arn:secret:odoo-eu1",
    )
    assert conn.connection_id.startswith("conn_")
    assert conn.status is ConnectionStatus.ACTIVE
    assert conn.is_active
    assert svc.get(conn.connection_id) is conn


def test_register_pause_resume_each_publish_a_fact_without_leaking_secrets() -> None:
    svc = _service()
    facts: CollectingFactPublisher = svc._facts  # type: ignore[attr-defined]
    conn = svc.register(
        erp_type=ErpType.ODOO,
        instance_label="Odoo EU-1",
        base_url="http://odoo:8069",
        credentials={"database": "odoo", "username": "admin"},
        secret_ref="arn:secret:odoo-eu1",
    )
    svc.pause(conn.connection_id)
    svc.resume(conn.connection_id)

    types = [f.event_type for f in facts.published]
    assert types == [CONNECTION_REGISTERED, CONNECTION_PAUSED, CONNECTION_RESUMED]
    for fact in facts.published:
        assert fact.payload["connection_id"] == str(conn.connection_id)
        assert "secret_ref" not in fact.payload
        assert "username" not in fact.payload


def test_secret_is_a_reference_not_a_raw_credential() -> None:
    conn = _service().register(
        erp_type=ErpType.ODOO,
        instance_label="Odoo US-1",
        base_url="https://odoo-us.example",
        credentials={"database": "odoo_us", "username": "api"},
        secret_ref="arn:secret:odoo-us1",
    )
    # secret_ref is a pointer; no plaintext password field exists on the model
    assert conn.secret_ref.startswith("arn:")
    assert not hasattr(conn, "password")
