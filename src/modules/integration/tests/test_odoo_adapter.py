"""Unit tests for OdooAdapter's pure logic and request-shaping, mocking the JSON-RPC
seam (`_authenticate`/`_execute`) rather than a live Odoo — these prove the adapter's own
decisions (idempotency, fail-closed product resolution, what fields fetch_status reads),
not Odoo's actual behavior. Live verification against a real Odoo remains separately
required before trusting this against production, per `docs/erps/odoo.md`.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from src.modules.integration.application.ports import ErpTarget
from src.modules.integration.infrastructure.odoo_adapter import OdooAdapter, build_sale_order_lines

_TARGET = ErpTarget(erp_type="ODOO", base_url="http://odoo", credentials={"database": "odoo", "username": "admin"}, secret="x")


def test_capabilities_are_declared() -> None:
    """ADR-0015: a declared, inspectable contract — not yet gated on, but real."""
    assert OdooAdapter.capabilities == {"tax", "uom", "idempotency", "fail_closed_product"}


def test_build_sale_order_lines_defaults_bad_quantity_to_one() -> None:
    lines = build_sale_order_lines({"lines": [{"product_key": "ANVIL", "quantity": "not-a-number"}]})
    assert lines == [
        {
            "product_key": "ANVIL",
            "quantity": 1.0,
            "unit_of_measure": "",
            "unit_price": None,
            "currency": None,
            "tax_codes": [],
        }
    ]


def test_build_sale_order_lines_nets_price_against_flat_discount() -> None:
    lines = build_sale_order_lines(
        {
            "lines": [
                {
                    "product_key": "ANVIL",
                    "quantity": 2,
                    "unit_of_measure": "EA",
                    "unit_price": {"amount": "19.99", "currency": "USD"},
                    "line_discount": {"amount": "2.00", "currency": "USD"},
                    "tax_rates": [{"code": "VAT", "rate": "0.20", "inclusive": False}],
                }
            ]
        }
    )
    assert lines[0]["unit_price"] == pytest.approx(17.99)
    assert lines[0]["currency"] == "USD"
    assert lines[0]["tax_codes"] == ["VAT"]


def test_submit_is_idempotent_on_platform_order_id() -> None:
    """A retried submit for the same order must return the existing Odoo order, not
    create a second one. The idempotency key is the platform order id (FR-A2), written to
    and searched on `client_order_ref`."""
    calls: list[tuple[str, str, list, dict | None]] = []

    def fake_execute(target: Any, uid: int, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        calls.append((model, method, args, kwargs))
        if model == "sale.order" and method == "search_read":
            return [{"name": "S00099"}]
        raise AssertionError(f"should not reach {model}.{method} once an existing order matches client_order_ref")

    adapter = OdooAdapter()
    with patch.object(OdooAdapter, "_authenticate", return_value=1), patch.object(
        OdooAdapter, "_execute", side_effect=fake_execute
    ):
        result = adapter.submit(_TARGET, {"order_id": "ord_123", "erp_customer_id": "5", "lines": []})

    assert result.success
    assert result.erp_order_id == "S00099"
    assert calls == [("sale.order", "search_read", [[["client_order_ref", "=", "ord_123"]]], {"fields": ["name"], "limit": 1})]


def test_submit_creates_as_the_erp_customer_without_name_lookup() -> None:
    """The customer is the binding's erp_customer_id sent as partner_id (FR-A1) — no
    res.partner search/create by name."""
    created_vals: dict[str, Any] = {}

    def fake_execute(target: Any, uid: int, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        if model == "sale.order" and method == "search_read":
            return []  # no existing order for this order_id
        if model == "res.partner":
            raise AssertionError("must not look up/create a partner by name — use erp_customer_id (FR-A1)")
        if model == "product.product" and method == "search":
            return [7]
        if model == "sale.order" and method == "create":
            created_vals.update(args[0])
            return 42
        if model == "sale.order" and method == "read":
            return [{"name": "S00001"}]
        raise AssertionError(f"unexpected call: {model}.{method}")

    adapter = OdooAdapter()
    with patch.object(OdooAdapter, "_authenticate", return_value=1), patch.object(
        OdooAdapter, "_execute", side_effect=fake_execute
    ):
        result = adapter.submit(
            _TARGET, {"order_id": "ord_2", "erp_customer_id": "5", "lines": [{"product_key": "ANVIL", "quantity": 2}]}
        )

    assert result.success
    assert result.erp_order_id == "S00001"
    assert created_vals["partner_id"] == 5  # the erp_customer_id, used directly
    assert created_vals["client_order_ref"] == "ord_2"


def test_submit_fails_closed_without_an_erp_customer_id() -> None:
    """No binding -> no erp_customer_id -> terminal error, never a nameless auto-created
    partner (FR-A1)."""

    def fake_execute(target: Any, uid: int, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        if model == "sale.order" and method == "search_read":
            return []
        raise AssertionError(f"must not proceed without a customer: {model}.{method}")

    adapter = OdooAdapter()
    with patch.object(OdooAdapter, "_authenticate", return_value=1), patch.object(
        OdooAdapter, "_execute", side_effect=fake_execute
    ):
        result = adapter.submit(_TARGET, {"order_id": "ord_x", "lines": [{"product_key": "ANVIL", "quantity": 1}]})

    assert not result.success
    assert result.terminal


def test_submit_resolves_price_uom_and_tax_onto_the_order_line() -> None:
    sent_line_vals: dict[str, Any] = {}

    def fake_execute(target: Any, uid: int, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        if model == "sale.order" and method == "search_read":
            return []
        if model == "product.product" and method == "search":
            return [7]
        if model == "uom.uom" and method == "search":
            assert args == [[["name", "=", "EA"]]]
            return [3]
        if model == "account.tax" and method == "search":
            assert args == [[["name", "=", "VAT"]]]
            return [9]
        if model == "sale.order" and method == "create":
            sent_line_vals.update(args[0]["order_line"][0][2])
            return 42
        if model == "sale.order" and method == "read":
            return [{"name": "S00001"}]
        raise AssertionError(f"unexpected call: {model}.{method}")

    adapter = OdooAdapter()
    with patch.object(OdooAdapter, "_authenticate", return_value=1), patch.object(
        OdooAdapter, "_execute", side_effect=fake_execute
    ):
        result = adapter.submit(
            _TARGET,
            {
                "order_id": "ord_4",
                "erp_customer_id": "5",
                "lines": [
                    {
                        "product_key": "ANVIL",
                        "quantity": 2,
                        "unit_of_measure": "EA",
                        "unit_price": {"amount": "19.99", "currency": "USD"},
                        "line_discount": {"amount": "2.00", "currency": "USD"},
                        "tax_rates": [{"code": "VAT", "rate": "0.20", "inclusive": False}],
                    }
                ],
            },
        )

    assert result.success
    assert sent_line_vals["price_unit"] == pytest.approx(17.99)
    assert sent_line_vals["product_uom"] == 3
    assert sent_line_vals["tax_id"] == [(6, 0, [9])]


def test_submit_omits_uom_and_tax_when_no_odoo_match_instead_of_failing() -> None:
    """Graceful degradation, unlike unknown-product: a UoM/tax naming mismatch doesn't
    block the order — the line just goes out with Odoo's default UoM / no tax."""

    def fake_execute(target: Any, uid: int, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        if model == "sale.order" and method == "search_read":
            return []
        if model == "product.product" and method == "search":
            return [7]
        if model in ("uom.uom", "account.tax") and method == "search":
            return []  # no match
        if model == "sale.order" and method == "create":
            return 42
        if model == "sale.order" and method == "read":
            return [{"name": "S00001"}]
        raise AssertionError(f"unexpected call: {model}.{method}")

    adapter = OdooAdapter()
    with patch.object(OdooAdapter, "_authenticate", return_value=1), patch.object(
        OdooAdapter, "_execute", side_effect=fake_execute
    ):
        result = adapter.submit(
            _TARGET,
            {
                "order_id": "ord_5",
                "erp_customer_id": "5",
                "lines": [
                    {
                        "product_key": "ANVIL",
                        "quantity": 1,
                        "unit_of_measure": "BOX",
                        "tax_rates": [{"code": "UNKNOWN-TAX", "rate": "0.20", "inclusive": False}],
                    }
                ],
            },
        )

    assert result.success  # not blocked despite no UoM/tax match


def test_submit_fails_closed_on_unknown_product_not_silent_auto_create() -> None:
    def fake_execute(target: Any, uid: int, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        if model == "sale.order" and method == "search_read":
            return []
        if model == "product.product" and method == "search":
            return []  # not found
        raise AssertionError(f"must not create a product — unexpected call: {model}.{method}")

    adapter = OdooAdapter()
    with patch.object(OdooAdapter, "_authenticate", return_value=1), patch.object(
        OdooAdapter, "_execute", side_effect=fake_execute
    ):
        result = adapter.submit(
            _TARGET, {"order_id": "ord_3", "erp_customer_id": "5", "lines": [{"product_key": "TYPO-SKU", "quantity": 1}]}
        )

    assert not result.success
    assert result.terminal
    assert "TYPO-SKU" in (result.error or "")


def test_fetch_status_returns_state_and_invoice_status() -> None:
    def fake_execute(target: Any, uid: int, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        assert kwargs == {"fields": ["state", "invoice_status"], "limit": 1}
        return [{"state": "sale", "invoice_status": "invoiced"}]

    adapter = OdooAdapter()
    with patch.object(OdooAdapter, "_authenticate", return_value=1), patch.object(
        OdooAdapter, "_execute", side_effect=fake_execute
    ):
        fields = adapter.fetch_status(_TARGET, "S00001")

    assert fields == {"state": "sale", "invoice_status": "invoiced"}


def test_fetch_status_returns_none_when_order_not_found() -> None:
    adapter = OdooAdapter()
    with patch.object(OdooAdapter, "_authenticate", return_value=1), patch.object(
        OdooAdapter, "_execute", return_value=[]
    ):
        assert adapter.fetch_status(_TARGET, "S00999") is None
