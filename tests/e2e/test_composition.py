"""Verifies the composition root wires a working graph: seed config, place an order,
drain the bus, and the reseller projection shows it reached the ERP."""

from __future__ import annotations

import os

from src.composition import build_container
from src.modules.catalog.domain.models import Item
from src.modules.connections.domain.models import ErpConnection, ErpType
from src.modules.ordering.domain.models import OrderLine
from src.modules.tenancy.domain.models import BindingStatus, TenantConnectionBinding
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
            database="odoo",
            username="admin",
            secret_ref="env:ODOO_SECRET",
        )
    )
    container.items.add(Item(item_id=ItemId("item_anvil"), sku="ANVIL", name="Anvil", owning_connection_id=conn))
    container.bindings.add(
        TenantConnectionBinding(
            binding_id=BindingId("bind_demo"),
            tenant_id=TenantId("tnt_demo"),
            connection_id=conn,
            erp_customer_id="CUST-1",
            status=BindingStatus.VERIFIED,
        )
    )

    order_id = container.order_service.place_order(
        tenant_id=TenantId("tnt_demo"),
        client_reference="PO-1",
        lines=[OrderLine(product_key="ANVIL", quantity=2, unit_of_measure="EA")],
    )
    container.bus.run_until_empty()

    view = container.projections.get_reseller_view("tnt_demo", order_id)
    assert view is not None
    assert view.status == "Sent to ERP"
