"""Smoke test for Phase 3 item B — the actual FastAPI app (not just `build_container`
directly) under both profiles, via `TestClient`. Catches what a container-only test
can't: resolvers that reach into `container.bus` directly instead of `container.drain()`.

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

try:
    _factory = get_session_factory()
    with _factory() as _probe:
        _probe.execute(text("SELECT 1"))
except Exception as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"Postgres not reachable: {exc}", allow_module_level=True)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _app(profile: str):
    os.environ["APP_PROFILE"] = profile
    os.environ["ERP_ADAPTER_MODE"] = "stub"  # no live Odoo/floci in this check
    get_settings.cache_clear()  # get_settings() is lru_cached — must re-read the new profile
    from src.api.app import create_app

    return create_app()


def _seed(container, tenant: str, connection: str, sku: str) -> None:
    from src.modules.catalog.domain.models import Item
    from src.modules.connections.domain.models import ErpConnection, ErpType
    from src.modules.tenancy.domain.models import BindingStatus, TenantConnectionBinding
    from src.shared.types import BindingId, ConnectionId, ItemId, TenantId

    os.environ["SMOKE_ODOO_SECRET"] = "local-secret"  # resolved via EnvSecretStore (memory profile)
    container.connections.add(
        ErpConnection(
            connection_id=ConnectionId(connection),
            erp_type=ErpType.ODOO,
            instance_label="Smoke Odoo",
            base_url="http://odoo:8069",
            database="odoo",
            username="admin",
            secret_ref="env:SMOKE_ODOO_SECRET",
        )
    )
    container.items.add(
        Item(item_id=ItemId(_id("item")), sku=sku, name="Widget", owning_connection_id=ConnectionId(connection))
    )
    container.bindings.add(
        TenantConnectionBinding(
            binding_id=BindingId(_id("bind")),
            tenant_id=TenantId(tenant),
            connection_id=ConnectionId(connection),
            erp_customer_id="CUST-1",
            status=BindingStatus.VERIFIED,
        )
    )


_PLACE_ORDER = """
mutation($ref: String!, $lines: [OrderLineInput!]!) {
  placeOrder(clientReference: $ref, lines: $lines)
}
"""

_GET_ORDER = """
query($id: String!) {
  order(orderId: $id) { orderId status lines { productKey quantity unitOfMeasure } timeline { status occurredAt } }
}
"""


def test_memory_profile_places_order_and_delivers_inline() -> None:
    from fastapi.testclient import TestClient

    app = _app("memory")
    tenant, connection, sku = _id("tnt"), _id("conn"), _id("SKU")
    _seed(app.state.container, tenant, connection, sku)

    client = TestClient(app)
    assert client.get("/livez").status_code == 200

    resp = client.post(
        "/graphql/reseller",
        json={"query": _PLACE_ORDER, "variables": {"ref": "PO-SMOKE", "lines": [{"productKey": sku, "quantity": 1, "unitOfMeasure": "EA"}]}},
        headers={"x-tenant-id": tenant},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("errors") is None, body
    order_id = body["data"]["placeOrder"]

    # memory profile drains inline (container.drain() -> bus.run_until_empty()) — by the
    # time the mutation returns, routing + stub-ERP delivery have already happened.
    view = app.state.container.projections.get_reseller_view(tenant, order_id)
    assert view is not None
    assert view.status == "Sent to ERP"

    # Through the actual GraphQL query resolver this time, not just the container — this
    # is what caught `OrderLineType(pos, pos, pos)` breaking under strawberry (types need
    # kwargs), which the container-only checks above never touch.
    resp = client.post("/graphql/reseller", json={"query": _GET_ORDER, "variables": {"id": order_id}}, headers={"x-tenant-id": tenant})
    assert resp.status_code == 200
    gql_body = resp.json()
    assert gql_body.get("errors") is None, gql_body
    assert gql_body["data"]["order"]["status"] == "Sent to ERP"
    assert gql_body["data"]["order"]["lines"] == [{"productKey": sku, "quantity": 1.0, "unitOfMeasure": "EA"}]


def test_postgres_profile_places_order_without_crashing_and_leaves_it_for_the_worker() -> None:
    from fastapi.testclient import TestClient

    app = _app("postgres")
    tenant, connection, sku = _id("tnt"), _id("conn"), _id("SKU")
    _seed(app.state.container, tenant, connection, sku)
    assert app.state.container.bus is None

    client = TestClient(app)
    resp = client.post(
        "/graphql/reseller",
        json={"query": _PLACE_ORDER, "variables": {"ref": "PO-SMOKE", "lines": [{"productKey": sku, "quantity": 1, "unitOfMeasure": "EA"}]}},
        headers={"x-tenant-id": tenant},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("errors") is None, body  # this is exactly what test_memory_profile catches if it regresses
    order_id = body["data"]["placeOrder"]

    try:
        # Nothing has processed it yet — no worker (item C) is running — so the event and
        # its outbox row exist, but the projection is still empty. That's the correct
        # handoff point.
        with _factory() as session:
            event_row = session.execute(
                text("SELECT event_type FROM events WHERE stream_id = :oid"), {"oid": order_id}
            ).fetchall()
            outbox_row = session.execute(
                text("SELECT published_at FROM outbox WHERE stream_id = :oid"), {"oid": order_id}
            ).fetchall()
        assert [r[0] for r in event_row] == ["OrderSubmitted"]
        assert len(outbox_row) == 1 and outbox_row[0][0] is None

        assert app.state.container.projections.get_reseller_view(tenant, order_id) is None
    finally:
        # This event/connection has no consumer of its own — item C's worker/relay would
        # otherwise pick up an unpublished outbox row and iterate a connection with a
        # fake secret_ref, crashing every reconcile/delivery attempt on real test data
        # left behind. Learned this the hard way; see aidlc-docs/audit.md.
        with _factory() as session, session.begin():
            session.execute(text("DELETE FROM outbox WHERE stream_id = :oid"), {"oid": order_id})
            session.execute(text("DELETE FROM events WHERE stream_id = :oid"), {"oid": order_id})
            # Also clean the projection, in case a worker happens to be running
            # concurrently against this same dev database and already consumed the event.
            session.execute(text("DELETE FROM order_status_history WHERE order_id = :oid"), {"oid": order_id})
            session.execute(text("DELETE FROM orders WHERE order_id = :oid"), {"oid": order_id})
            session.execute(
                text("DELETE FROM tenant_connection_bindings WHERE connection_id = :cid"), {"cid": connection}
            )
            session.execute(text("DELETE FROM items WHERE owning_connection_id = :cid"), {"cid": connection})
            session.execute(text("DELETE FROM erp_connections WHERE connection_id = :cid"), {"cid": connection})
