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

from datetime import date, timedelta  # noqa: E402
from decimal import Decimal  # noqa: E402

from sqlalchemy import text  # noqa: E402
from src.composition import build_container  # noqa: E402
from src.modules.reference.connections.domain.models import ErpConnection, ErpType  # noqa: E402
from src.modules.reference.tenancy.domain.models import (  # noqa: E402
    BindingStatus,
    TenantConnectionBinding,
)
from src.modules.sales.ordering.application.order_service import OrderLineInput  # noqa: E402
from src.modules.sales.quoting.domain.models import EndCustomer, QuoteLine  # noqa: E402
from src.shared.config import Settings  # noqa: E402
from src.shared.money import Money  # noqa: E402
from src.shared.persistence.engine import get_session_factory  # noqa: E402
from src.shared.persistence.event_store import PostgresEventStore  # noqa: E402
from src.shared.types import BindingId, ConnectionId, TenantId  # noqa: E402

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
        worker_roles=base.worker_roles,
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
            credentials={"database": "odoo", "username": "admin"},
            secret_ref="env:ODOO_SECRET_UNUSED",
        )
    )
    sku = _id("ANVIL")
    container.bindings.add(
        TenantConnectionBinding(
            binding_id=BindingId(_id("bind")),
            tenant_id=tenant,
            connection_id=connection,
            erp_customer_id="CUST-1",
            status=BindingStatus.VERIFIED,
        )
    )

    # Increment 5: an order replies to a quote — price/UoM come from it, never the
    # reseller's own input (ADR-0011/ADR-0016). Issue one priced line for `sku`.
    company = container.quote_service.create_subsidiary(
        name="Test Distributor", country="US", language="en"
    )
    container.quote_service.set_erp_route(company.subsidiary_id, str(connection))
    quote = container.quote_service.issue_quote(
        tenant_id=tenant,
        subsidiary_id=company.subsidiary_id,
        end_customer=EndCustomer(name="Downstream Co", ship_to="1 Main St"),
        currency="USD",
        valid_from=date.today() - timedelta(days=1),
        valid_until=date.today() + timedelta(days=30),
        lines=[
            QuoteLine(
                product_key=sku, unit_price=Money(Decimal("19.99"), "USD"), unit_of_measure="EA"
            )
        ],
    )

    order_id = container.order_service.place_order(
        tenant_id=tenant,
        quote_id=quote.quote_id,
        client_reference="PO-1",
        lines=[OrderLineInput(sku, Decimal(2))],
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
        assert [e.event_type for e in events] == [
            "OrderSubmitted",
            "OrderValidated",
            "OrderReadyForDelivery",
        ]
        for event in events:
            container.order_projector.handle(event)

        operator = container.projections.get_operator_view(order_id)
        assert operator is not None
        assert operator.status == "VALIDATED"
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
            session.execute(
                text("DELETE FROM order_status_history WHERE order_id = :oid"), {"oid": order_id}
            )
            session.execute(text("DELETE FROM orders WHERE order_id = :oid"), {"oid": order_id})
            session.execute(
                text("DELETE FROM quotes WHERE quote_id = :qid"), {"qid": quote.quote_id}
            )
            session.execute(
                text("DELETE FROM subsidiary_routes WHERE subsidiary_id = :ocid"),
                {"ocid": company.subsidiary_id},
            )
            session.execute(
                text("DELETE FROM subsidiaries WHERE subsidiary_id = :ocid"),
                {"ocid": company.subsidiary_id},
            )
            session.execute(
                text("DELETE FROM tenant_connection_bindings WHERE connection_id = :cid"),
                {"cid": str(connection)},
            )
            session.execute(
                text("DELETE FROM erp_connections WHERE connection_id = :cid"),
                {"cid": str(connection)},
            )


def test_postgres_profile_rejects_a_reused_order_number() -> None:
    """Gap #3 (architect review, 2026-10-04): a reseller's own order number had no
    uniqueness check. OrderService.place_order now refuses a repeat before anything is
    written — proved here against the real projection store, not just in-memory."""
    from src.modules.sales.ordering.domain.errors import DuplicateOrderReference

    container = build_container(_postgres_settings())
    tenant = TenantId(_id("tnt"))
    company = container.quote_service.create_subsidiary(
        name="Test Distributor", country="US", language="en"
    )
    container.quote_service.set_erp_route(company.subsidiary_id, _id("conn"))

    def _issue_quote():
        return container.quote_service.issue_quote(
            tenant_id=tenant,
            subsidiary_id=company.subsidiary_id,
            end_customer=EndCustomer(name="Downstream Co", ship_to="1 Main St"),
            currency="USD",
            valid_from=date.today() - timedelta(days=1),
            valid_until=date.today() + timedelta(days=30),
            lines=[
                QuoteLine(
                    product_key="ANVIL",
                    unit_price=Money(Decimal("19.99"), "USD"),
                    unit_of_measure="EA",
                )
            ],
        )

    # Two separate quotes: a quote is single-use (mark_accepted after its first order),
    # so re-using one isn't the scenario here — the repeated PO number is.
    quote = _issue_quote()
    quote2 = _issue_quote()
    order_id = container.order_service.place_order(
        tenant_id=tenant,
        quote_id=quote.quote_id,
        client_reference="PO-DUP",
        lines=[OrderLineInput("ANVIL", Decimal(1))],
    )
    try:
        # Postgres profile has no synchronous bus (container.bus is None) — nothing
        # projects the order unless driven manually, same as the test above. exists()
        # reads the projection, so it must be created before the duplicate check means
        # anything here.
        event_store = PostgresEventStore(_factory)
        for event in event_store.load(order_id):
            container.order_projector.handle(event)

        with pytest.raises(DuplicateOrderReference):
            container.order_service.place_order(
                tenant_id=tenant,
                quote_id=quote2.quote_id,
                client_reference="PO-DUP",
                lines=[OrderLineInput("ANVIL", Decimal(1))],
            )
    finally:
        with _factory() as session, session.begin():
            session.execute(text("DELETE FROM outbox WHERE stream_id = :oid"), {"oid": order_id})
            session.execute(text("DELETE FROM events WHERE stream_id = :oid"), {"oid": order_id})
            session.execute(
                text("DELETE FROM order_status_history WHERE order_id = :oid"), {"oid": order_id}
            )
            session.execute(text("DELETE FROM orders WHERE order_id = :oid"), {"oid": order_id})
            session.execute(
                text("DELETE FROM quotes WHERE quote_id IN (:q1, :q2)"),
                {"q1": quote.quote_id, "q2": quote2.quote_id},
            )
            session.execute(
                text("DELETE FROM subsidiary_routes WHERE subsidiary_id = :ocid"),
                {"ocid": company.subsidiary_id},
            )
            session.execute(
                text("DELETE FROM subsidiaries WHERE subsidiary_id = :ocid"),
                {"ocid": company.subsidiary_id},
            )
