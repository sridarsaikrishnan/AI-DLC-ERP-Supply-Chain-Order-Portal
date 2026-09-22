"""U2 tests: catalog seed, canonical validation gate, corrective-state gating. DB-free where possible."""

import pytest

from src.modules.foundation.canonical.models import (
    Address,
    CanonicalOrderLine,
    CanonicalSalesOrder,
)
from src.modules.foundation.canonical.validator import validate_sales_order
from src.modules.ordering.catalog_service import CatalogService


def test_catalog_browse_and_filter():
    svc = CatalogService()
    assert len(svc.browse()) >= 1
    assert all("widget" in p["name"].lower() for p in svc.browse("widget"))


def test_inventory_lookup():
    svc = CatalogService()
    inv = svc.availability("P1")
    assert inv and inv["available_quantity"] >= 0
    assert svc.availability("does-not-exist") is None


def test_place_order_validation_rejects_bad_order():
    # A canonical order with no line items must fail U0 validation (which OrderService enforces)
    from datetime import date

    order = CanonicalSalesOrder(
        tenant_id="t1",
        client_reference="PO-1",
        order_date=date(2026, 1, 1),
        ship_to=Address(name="ACME", lines=["1 Main"], city="Metro", country="US"),
        currency="USD",
        line_items=[],
    )
    errors = validate_sales_order(order)
    assert any(e["path"] == "line_items" for e in errors)


def test_place_order_validation_accepts_good_order():
    from datetime import date

    order = CanonicalSalesOrder(
        tenant_id="t1",
        client_reference="PO-1",
        order_date=date(2026, 1, 1),
        ship_to=Address(name="ACME", lines=["1 Main"], city="Metro", country="US"),
        currency="USD",
        line_items=[CanonicalOrderLine(product_key="P1", quantity=3, unit_of_measure="EA")],
    )
    assert validate_sales_order(order, today=date(2026, 1, 1)) == []
