"""Verifies the composition root wires a working graph: seed config + a quote, place an
order against the quote, drain the bus, and the reseller projection shows it reached the ERP."""

from __future__ import annotations

import os
from datetime import date, timedelta
from decimal import Decimal

from src.composition import build_container
from src.modules.catalog.domain.models import Item
from src.modules.connections.domain.models import ErpConnection, ErpType
from src.modules.ordering.application.order_service import OrderLineInput
from src.modules.quoting.domain.models import EndCustomer, QuoteLine
from src.modules.tenancy.domain.models import BindingStatus, TenantConnectionBinding
from src.shared.money import Money
from src.shared.types import BindingId, ConnectionId, ItemId, TenantId


def test_container_places_routes_and_delivers() -> None:
    os.environ["ODOO_SECRET"] = "local-secret"
    container = build_container()

    conn = ConnectionId("conn_odoo_local")
    container.connections.add(
        ErpConnection(
            connection_id=conn,
            erp_type=ErpType.ODOO,
            instance_label="Local Odoo",
            base_url="http://odoo:8069",
            credentials={"database": "odoo", "username": "admin"},
            secret_ref="env:ODOO_SECRET",
        )
    )
    container.items.add(
        Item(item_id=ItemId("item_anvil"), sku="ANVIL", name="Anvil", owning_connection_id=conn)
    )
    container.bindings.add(
        TenantConnectionBinding(
            binding_id=BindingId("bind_demo"),
            tenant_id=TenantId("tnt_demo"),
            connection_id=conn,
            erp_customer_id="CUST-1",
            status=BindingStatus.VERIFIED,
        )
    )

    company = container.quote_service.create_operating_company(
        name="Distributor Co", country="US", language="en"
    )
    quote = container.quote_service.issue_quote(
        tenant_id=TenantId("tnt_demo"),
        operating_company_id=company.operating_company_id,
        end_customer=EndCustomer(name="Downstream Inc", ship_to="1 Main St"),
        currency="USD",
        valid_from=date.today() - timedelta(days=1),
        valid_until=date.today() + timedelta(days=30),
        lines=[
            QuoteLine(
                product_key="ANVIL", unit_price=Money(Decimal("19.99"), "USD"), unit_of_measure="EA"
            )
        ],
    )

    order_id = container.order_service.place_order(
        tenant_id=TenantId("tnt_demo"),
        quote_id=quote.quote_id,
        client_reference="PO-1",
        lines=[OrderLineInput("ANVIL", Decimal(2))],
    )
    container.bus.run_until_empty()

    view = container.projections.get_reseller_view("tnt_demo", order_id)
    assert view is not None
    assert view.status == "Sent to ERP"
    assert view.parties.end_customer_name == "Downstream Inc"
