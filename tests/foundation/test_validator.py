"""Unit tests for canonical validation (BR-1)."""

from datetime import date, datetime, timezone

from src.modules.foundation.canonical.models import (
    Address,
    CanonicalOrderLine,
    CanonicalOrderStatus,
    CanonicalSalesOrder,
    LifecycleState,
)
from src.modules.foundation.canonical.validator import (
    validate_order_status,
    validate_sales_order,
)


def _valid_order() -> CanonicalSalesOrder:
    return CanonicalSalesOrder(
        tenant_id="t1",
        client_reference="PO-100",
        order_date=date(2026, 1, 1),
        ship_to=Address(name="ACME", lines=["1 Main St"], city="Metro", country="US"),
        currency="USD",
        line_items=[CanonicalOrderLine(product_key="P1", quantity=2, unit_of_measure="EA")],
    )


def test_valid_order_passes():
    assert validate_sales_order(_valid_order(), today=date(2026, 1, 1)) == []


def test_missing_line_items_fails():
    order = _valid_order()
    order.line_items = []
    errors = validate_sales_order(order)
    assert any(e["path"] == "line_items" for e in errors)


def test_bad_currency_fails():
    order = _valid_order()
    order.currency = "US"
    errors = validate_sales_order(order)
    assert any(e["path"] == "currency" for e in errors)


def test_zero_quantity_fails():
    order = _valid_order()
    order.line_items[0].quantity = 0
    errors = validate_sales_order(order)
    assert any("quantity" in e["path"] for e in errors)


def test_past_requested_date_fails():
    order = _valid_order()
    order.line_items[0].requested_date = date(2025, 1, 1)
    errors = validate_sales_order(order, today=date(2026, 1, 1))
    assert any("requested_date" in e["path"] for e in errors)


def test_accepted_status_requires_erp_reference():
    status = CanonicalOrderStatus(
        order_id="o1", state=LifecycleState.ACCEPTED, occurred_at=datetime.now(timezone.utc)
    )
    errors = validate_order_status(status)
    assert any(e["path"] == "erp_reference" for e in errors)
