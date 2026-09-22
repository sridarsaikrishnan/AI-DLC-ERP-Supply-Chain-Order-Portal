"""Property-based tests (partial PBT scope): validation invariants and
canonical serialization round-trips.
"""

from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from src.modules.foundation.canonical.models import (
    Address,
    CanonicalOrderLine,
    CanonicalSalesOrder,
)
from src.modules.foundation.canonical.validator import validate_sales_order


# --- Property 1: a well-formed order with positive quantities and valid fields always validates ---
@given(
    qty=st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
    ref=st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != ""),
)
def test_wellformed_order_always_valid(qty, ref):
    order = CanonicalSalesOrder(
        tenant_id="t1",
        client_reference=ref,
        order_date=date(2026, 1, 1),
        ship_to=Address(name="ACME", lines=["1 Main St"], city="Metro", country="US"),
        currency="USD",
        line_items=[CanonicalOrderLine(product_key="P1", quantity=qty, unit_of_measure="EA")],
    )
    assert validate_sales_order(order, today=date(2026, 1, 1)) == []


# --- Property 2: canonical order survives a JSON serialization round-trip ---
@given(
    ref=st.text(min_size=1, max_size=20),
    qty=st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def test_order_json_roundtrip(ref, qty):
    order = CanonicalSalesOrder(
        tenant_id="t1",
        client_reference=ref,
        order_date=date(2026, 1, 1),
        ship_to=Address(name="ACME", lines=["1 Main St"], city="Metro", country="US"),
        currency="USD",
        line_items=[CanonicalOrderLine(product_key="P1", quantity=qty, unit_of_measure="EA")],
    )
    restored = CanonicalSalesOrder.model_validate_json(order.model_dump_json())
    assert restored == order
