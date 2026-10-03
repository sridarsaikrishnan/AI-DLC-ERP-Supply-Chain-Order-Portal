"""Integration test for Phase 3 item D — Odoo shared-secret-in-path webhook auth.

End-to-end through the REAL HTTP route (not just the application-layer unit tests in
`webhooks_inbound/tests/test_ingress.py`): place an order, manually drive it to
SENT_TO_ERP (same "drive it like the worker will" pattern as
`test_postgres_composition.py` — no worker runs in this test), then POST a real HTTP
webhook to `/erp/webhook/{connection_id}/{webhook_secret}` simulating Odoo pushing a
status change, and confirm it updates the projected order status.

Self-skips like the other integration tests when Postgres/deps aren't reachable.
"""

from __future__ import annotations

import os
import uuid

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("httpx")

from sqlalchemy import text  # noqa: E402

from src.shared.config import get_settings  # noqa: E402
from src.shared.persistence.engine import get_session_factory  # noqa: E402
from src.shared.persistence.event_store import PostgresEventStore  # noqa: E402

try:
    _factory = get_session_factory()
    with _factory() as _probe:
        _probe.execute(text("SELECT 1"))
except Exception as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"Postgres not reachable: {exc}", allow_module_level=True)

_AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")
if not _AWS_ENDPOINT_URL:
    # This test creates/deletes real Secrets Manager secrets. Without an explicit
    # endpoint_url, boto3 falls back to REAL AWS — never let that happen implicitly.
    pytest.skip("AWS_ENDPOINT_URL not set (must point at floci, not real AWS)", allow_module_level=True)

try:
    import boto3

    _floci = boto3.client("secretsmanager", endpoint_url=_AWS_ENDPOINT_URL, region_name="us-east-1")
    _floci.list_secrets(MaxResults=1)
except Exception as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"floci/Secrets Manager not reachable: {exc}", allow_module_level=True)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _app():
    os.environ["APP_PROFILE"] = "postgres"
    os.environ["ERP_ADAPTER_MODE"] = "stub"
    get_settings.cache_clear()
    from src.api.app import create_app

    return create_app()


def test_odoo_webhook_with_correct_shared_secret_updates_order_status() -> None:
    from fastapi.testclient import TestClient

    from src.modules.catalog.domain.models import Item
    from src.modules.connections.domain.models import ErpConnection, ErpType
    from src.modules.tenancy.domain.models import BindingStatus, TenantConnectionBinding
    from src.shared.types import BindingId, ConnectionId, ItemId, TenantId

    app = _app()
    container = app.state.container

    tenant, connection, sku = _id("tnt"), _id("conn"), _id("SKU")
    webhook_secret = _id("whsec")
    webhook_secret_name = f"local:test-webhook-{uuid.uuid4().hex[:8]}"
    login_secret_name = f"local:test-login-{uuid.uuid4().hex[:8]}"
    _floci.create_secret(Name=webhook_secret_name, SecretString=webhook_secret)
    # DeliveryHandler resolves this too (to build the ErpTarget) even though the stub
    # adapter never uses the value — it just needs to resolve without raising.
    _floci.create_secret(Name=login_secret_name, SecretString="unused-in-stub-mode")

    connection_id = ConnectionId(connection)
    container.connections.add(
        ErpConnection(
            connection_id=connection_id,
            erp_type=ErpType.ODOO,
            instance_label="Webhook Test Odoo",
            base_url="http://odoo:8069",
            credentials={"database": "odoo", "username": "admin"},
            secret_ref=login_secret_name,
            webhook_secret_ref=webhook_secret_name,
        )
    )
    container.items.add(Item(item_id=ItemId(_id("item")), sku=sku, name="Widget", owning_connection_id=connection_id))
    container.bindings.add(
        TenantConnectionBinding(
            binding_id=BindingId(_id("bind")),
            tenant_id=TenantId(tenant),
            connection_id=connection_id,
            erp_customer_id="CUST-1",
            status=BindingStatus.VERIFIED,
        )
    )

    client = TestClient(app)
    order_id = None
    try:
        resp = client.post(
            "/graphql/reseller",
            json={
                "query": "mutation($ref:String!,$lines:[OrderLineInput!]!){ placeOrder(clientReference:$ref, lines:$lines) }",
                "variables": {"ref": "PO-WEBHOOK", "lines": [{"productKey": sku, "quantity": 1, "unitOfMeasure": "EA"}]},
            },
            headers={"x-tenant-id": tenant},
        )
        order_id = resp.json()["data"]["placeOrder"]

        # Drive the order to SENT_TO_ERP the way the worker (item C) would, so there's a
        # real (connection, erp_order_id) reverse-routing pivot for the webhook to attribute.
        event_store = PostgresEventStore(_factory)
        container.order_processor.handle(event_store.load(order_id)[0])
        events = event_store.load(order_id)
        for event in events:
            container.order_projector.handle(event)
        container.delivery_handler.handle(events[-1])  # OrderReadyForDelivery -> stub ERP submit
        for event in event_store.load(order_id)[len(events) :]:
            container.order_projector.handle(event)

        erp_order_id = container.projections.get_operator_view(order_id).erp_order_id
        assert erp_order_id is not None

        # The actual point of this test: a real HTTP POST to the shared-secret route.
        pre_webhook_events = event_store.load(order_id)
        resp = client.post(
            f"/erp/webhook/{connection}/{webhook_secret}",
            json={"erp_order_id": erp_order_id, "state": "sale", "event_id": _id("evt")},
        )
        assert resp.status_code == 200, resp.text

        # Wrong secret must be rejected, not silently accepted.
        resp = client.post(
            f"/erp/webhook/{connection}/wrong-secret",
            json={"erp_order_id": erp_order_id, "state": "sale", "event_id": _id("evt")},
        )
        assert resp.status_code == 401

        # The webhook's status update landed as a new event (StatusApplier.apply_status ->
        # OrderConfirmed) — project it, the way the worker's projections consumer would.
        new_events = event_store.load(order_id)[len(pre_webhook_events) :]
        assert [e.event_type for e in new_events] == ["OrderConfirmed"]
        for event in new_events:
            container.order_projector.handle(event)

        operator = container.projections.get_operator_view(order_id)
        assert operator.status == "Confirmed"
    finally:
        _floci.delete_secret(SecretId=webhook_secret_name, ForceDeleteWithoutRecovery=True)
        _floci.delete_secret(SecretId=login_secret_name, ForceDeleteWithoutRecovery=True)
        if order_id is not None:
            with _factory() as session, session.begin():
                session.execute(text("DELETE FROM outbox WHERE stream_id = :oid"), {"oid": order_id})
                session.execute(text("DELETE FROM events WHERE stream_id = :oid"), {"oid": order_id})
                session.execute(text("DELETE FROM order_status_history WHERE order_id = :oid"), {"oid": order_id})
                session.execute(text("DELETE FROM orders WHERE order_id = :oid"), {"oid": order_id})
        with _factory() as session, session.begin():
            session.execute(
                text("DELETE FROM tenant_connection_bindings WHERE connection_id = :cid"), {"cid": connection}
            )
            session.execute(text("DELETE FROM items WHERE owning_connection_id = :cid"), {"cid": connection})
            session.execute(text("DELETE FROM erp_connections WHERE connection_id = :cid"), {"cid": connection})
