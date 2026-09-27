"""Integration test for Phase 3 item B — `build_container(profile="postgres")`.

Proves the postgres-profile wiring is correct: real `OrderService` + `OrderProcessor` +
the item-A Postgres repos/projection store, all reached through the same composition
root as the memory profile. Self-skips like `test_postgres_adapters.py` when Postgres/
deps aren't reachable.

Scope: routing (`order_processor`) only, not delivery. `DeliveryHandler` resolves a
connection's secret via `SecretsManagerSecretStore` (boto3 -> Secrets Manager/floci),
which isn't up in this check — that needs floci and belongs to item I (full E2E
verification), not this composition-wiring check.
"""

from __future__ import annotations

import uuid

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import text  # noqa: E402

from src.composition import build_container  # noqa: E402
from src.modules.catalog.domain.models import Item  # noqa: E402
from src.modules.connections.domain.models import ErpConnection, ErpType  # noqa: E402
from src.modules.ordering.domain.models import OrderLine  # noqa: E402
from src.modules.tenancy.domain.models import BindingStatus, TenantConnectionBinding  # noqa: E402
from src.shared.config import Settings  # noqa: E402
from src.shared.persistence.engine import get_session_factory  # noqa: E402
from src.shared.persistence.event_store import PostgresEventStore  # noqa: E402
from src.shared.types import BindingId, ConnectionId, ItemId, TenantId  # noqa: E402

try:
    _factory = get_session_factory()
    with _factory() as _probe:
        _probe.execute(text("SELECT 1"))
except Exception as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"Postgres not reachable: {exc}", allow_module_level=True)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _postgres_settings() -> Settings:
    from src.shared.config import get_settings

    base = get_settings()  # picks up DATABASE_URL etc. already set for this process
    return Settings(
        profile="postgres",
        database_url=base.database_url,
        aws_endpoint_url=base.aws_endpoint_url,
        aws_region=base.aws_region,
        domain_topic_arn=base.domain_topic_arn,
        erp_adapter_mode="stub",
        erp_odoo_timeout_seconds=base.erp_odoo_timeout_seconds,
        log_level=base.log_level,
        reconcile_interval_seconds=base.reconcile_interval_seconds,
        cognito_user_pool_id=base.cognito_user_pool_id,
        cognito_client_id=base.cognito_client_id,
        cognito_resource_server_id=base.cognito_resource_server_id,
        cors_allowed_origins=base.cors_allowed_origins,
    )


def test_postgres_profile_places_and_routes_an_order() -> None:
    container = build_container(_postgres_settings())
    assert container.bus is None  # postgres profile: no synchronous in-memory bus
    container.drain()  # no-op; must not raise

    tenant = TenantId(_id("tnt"))
    connection = ConnectionId(_id("conn"))
    container.connections.add(
        ErpConnection(
            connection_id=connection,
            erp_type=ErpType.ODOO,
            instance_label="Test Odoo",
            base_url="http://odoo:8069",
            database="odoo",
            username="admin",
            secret_ref="env:ODOO_SECRET_UNUSED",
        )
    )
    sku = _id("ANVIL")
    container.items.add(Item(item_id=ItemId(_id("item")), sku=sku, name="Anvil", owning_connection_id=connection))
    container.bindings.add(
        TenantConnectionBinding(
            binding_id=BindingId(_id("bind")),
            tenant_id=tenant,
            connection_id=connection,
            erp_customer_id="CUST-1",
            status=BindingStatus.VERIFIED,
        )
    )

    order_id = container.order_service.place_order(
        tenant_id=tenant,
        client_reference="PO-1",
        lines=[OrderLine(product_key=sku, quantity=2, unit_of_measure="EA")],
    )
    try:
        # Nothing auto-delivers in the postgres profile (no bus) — item C's worker would
        # normally do this via SQS consumers. Drive it manually here to prove the same
        # handler instances the worker will use are wired correctly against Postgres.
        event_store = PostgresEventStore(_factory)
        submitted = event_store.load(order_id)
        assert [e.event_type for e in submitted] == ["OrderSubmitted"]
        container.order_processor.handle(submitted[0])

        events = event_store.load(order_id)
        assert [e.event_type for e in events] == ["OrderSubmitted", "OrderValidated", "OrderReadyForDelivery"]
        for event in events:
            container.order_projector.handle(event)

        operator = container.projections.get_operator_view(order_id)
        assert operator is not None
        assert operator.status == "Validated"
        assert operator.owning_connection_id == str(connection)
    finally:
        # This order/connection has no consumer of its own; leaving rows behind would
        # make item C's worker (which iterates ALL active connections, and the relay
        # picks up ALL unpublished outbox rows) trip over test data on its next run —
        # a stray connection with a fake secret_ref crashes every reconcile/delivery
        # attempt. Learned this the hard way; see aidlc-docs/audit.md.
        with _factory() as session, session.begin():
            session.execute(text("DELETE FROM outbox WHERE stream_id = :oid"), {"oid": order_id})
            session.execute(text("DELETE FROM events WHERE stream_id = :oid"), {"oid": order_id})
            session.execute(text("DELETE FROM order_status_history WHERE order_id = :oid"), {"oid": order_id})
            session.execute(text("DELETE FROM orders WHERE order_id = :oid"), {"oid": order_id})
            session.execute(
                text("DELETE FROM tenant_connection_bindings WHERE connection_id = :cid"),
                {"cid": str(connection)},
            )
            session.execute(text("DELETE FROM items WHERE owning_connection_id = :cid"), {"cid": str(connection)})
            session.execute(text("DELETE FROM erp_connections WHERE connection_id = :cid"), {"cid": str(connection)})
