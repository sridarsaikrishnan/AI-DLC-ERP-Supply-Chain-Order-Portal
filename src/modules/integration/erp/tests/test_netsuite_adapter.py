"""Unit tests for NetSuiteAdapter's pure logic and request-shaping, mocking the OAuth2
token fetch (`_get_access_token`) and the REST seam (`_http`) rather than a live
NetSuite account — these prove the adapter's own decisions (idempotency, fail-closed
item resolution, what fields fetch_status reads/the status mapper uses), not NetSuite's
actual behavior. Live verification against a real NetSuite account remains separately
required before trusting this against production, per `docs/erps/netsuite.md`.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from src.modules.integration.erp.application.ports import ErpTarget
from src.modules.integration.erp.infrastructure.netsuite_adapter import (
    NetSuiteAdapter,
    build_sales_order_lines,
)

_TARGET = ErpTarget(
    erp_type="NETSUITE",
    base_url="https://1234567.suitetalk.api.netsuite.com",
    credentials={"account_id": "1234567", "client_id": "cid", "certificate_id": "kid1"},
    secret="not-a-real-private-key",
)

def test_capabilities_are_declared() -> None:
    """ADR-0015: a declared, inspectable contract — not yet gated on, but real."""
    assert NetSuiteAdapter.capabilities == {
        "idempotency",
        "fail_closed_product",
        "partial_fulfillment",
    }


def test_build_sales_order_lines_defaults_bad_quantity_to_one() -> None:
    lines = build_sales_order_lines(
        {"lines": [{"product_key": "ANVIL", "quantity": "not-a-number"}]}
    )
    assert lines == [
        {"product_key": "ANVIL", "quantity": 1.0, "unit_of_measure": "", "rate": None}
    ]


def test_build_sales_order_lines_reads_rate_from_unit_price() -> None:
    lines = build_sales_order_lines(
        {
            "lines": [
                {
                    "product_key": "ANVIL",
                    "quantity": 2,
                    "unit_of_measure": "EA",
                    "unit_price": {"amount": "19.99", "currency": "USD"},
                }
            ]
        }
    )
    assert lines[0]["rate"] == pytest.approx(19.99)
    assert lines[0]["unit_of_measure"] == "EA"


def test_submit_is_idempotent_on_platform_order_id() -> None:
    """A retried submit for the same order must return the existing NetSuite order, not
    create a second one. NetSuite's own `externalId` addressing is the idempotency key —
    not `otherrefnum` (that's approved to mean client_reference, a different field)."""
    calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def fake_http(target: Any, token: str, method: str, path: str, **kwargs: Any) -> Any:
        calls.append((method, path, kwargs.get("body")))
        if method == "GET" and path == "/record/v1/salesOrder/eid:ord_123":
            return 200, {"tranid": "SO0099"}, {}
        raise AssertionError(f"should not reach {method} {path} once externalId matches")

    adapter = NetSuiteAdapter()
    with (
        patch.object(NetSuiteAdapter, "_get_access_token", return_value="tok"),
        patch.object(NetSuiteAdapter, "_http", side_effect=fake_http),
    ):
        result = adapter.submit(
            _TARGET, {"order_id": "ord_123", "erp_customer_id": "5", "lines": []}
        )

    assert result.success
    assert result.erp_order_id == "SO0099"
    assert calls == [("GET", "/record/v1/salesOrder/eid:ord_123", None)]


def test_submit_creates_as_the_erp_customer_without_name_lookup() -> None:
    """`entityid` is the binding's erp_customer_id, sent directly (FR-A1) — no
    customer-record search/create by name."""
    created_body: dict[str, Any] = {}

    def fake_http(target: Any, token: str, method: str, path: str, **kwargs: Any) -> Any:
        if method == "GET" and path == "/record/v1/salesOrder/eid:ord_2":
            return 404, None, {}
        if method == "POST" and path == "/query/v1/suiteql":
            assert "item" in kwargs["body"]["q"]
            return 200, {"items": [{"id": "7"}]}, {}
        if method == "POST" and path == "/record/v1/salesOrder":
            created_body.update(kwargs["body"])
            return 204, None, {"Location": ".../record/v1/salesOrder/42"}
        if method == "GET" and path == "/record/v1/salesOrder/42":
            return 200, {"tranid": "SO0001"}, {}
        raise AssertionError(f"unexpected call: {method} {path}")

    adapter = NetSuiteAdapter()
    with (
        patch.object(NetSuiteAdapter, "_get_access_token", return_value="tok"),
        patch.object(NetSuiteAdapter, "_http", side_effect=fake_http),
    ):
        result = adapter.submit(
            _TARGET,
            {
                "order_id": "ord_2",
                "erp_customer_id": "5",
                "client_reference": "PO-99",
                "lines": [{"product_key": "ANVIL", "quantity": 2}],
            },
        )

    assert result.success
    assert result.erp_order_id == "SO0001"
    assert created_body["entityid"] == "5"  # the erp_customer_id, used directly
    assert created_body["otherrefnum"] == "PO-99"
    assert created_body["externalId"] == "ord_2"
    assert created_body["item"]["items"][0]["item"] == {"id": "7"}
    assert "units" not in created_body["item"]["items"][0]  # _resolve_unit always omits


def test_submit_fails_closed_without_an_erp_customer_id() -> None:
    """No binding -> no erp_customer_id -> terminal error, never a nameless auto-created
    customer (FR-A1)."""

    def fake_http(target: Any, token: str, method: str, path: str, **kwargs: Any) -> Any:
        if method == "GET" and path == "/record/v1/salesOrder/eid:ord_x":
            return 404, None, {}
        raise AssertionError(f"must not proceed without a customer: {method} {path}")

    adapter = NetSuiteAdapter()
    with (
        patch.object(NetSuiteAdapter, "_get_access_token", return_value="tok"),
        patch.object(NetSuiteAdapter, "_http", side_effect=fake_http),
    ):
        result = adapter.submit(
            _TARGET, {"order_id": "ord_x", "lines": [{"product_key": "ANVIL", "quantity": 1}]}
        )

    assert not result.success
    assert result.terminal


def test_submit_fails_closed_on_unknown_item_not_silent_auto_create() -> None:
    def fake_http(target: Any, token: str, method: str, path: str, **kwargs: Any) -> Any:
        if method == "GET" and path == "/record/v1/salesOrder/eid:ord_3":
            return 404, None, {}
        if method == "POST" and path == "/query/v1/suiteql":
            return 200, {"items": []}, {}  # not found
        raise AssertionError(f"must not create an item — unexpected call: {method} {path}")

    adapter = NetSuiteAdapter()
    with (
        patch.object(NetSuiteAdapter, "_get_access_token", return_value="tok"),
        patch.object(NetSuiteAdapter, "_http", side_effect=fake_http),
    ):
        result = adapter.submit(
            _TARGET,
            {
                "order_id": "ord_3",
                "erp_customer_id": "5",
                "lines": [{"product_key": "TYPO-SKU", "quantity": 1}],
            },
        )

    assert not result.success
    assert result.terminal
    assert "TYPO-SKU" in (result.error or "")


def test_fetch_status_returns_fulfillmentstatus_carrier_and_shipqty() -> None:
    def fake_http(target: Any, token: str, method: str, path: str, **kwargs: Any) -> Any:
        if method == "POST" and path == "/query/v1/suiteql":
            assert kwargs["extra_headers"] == {"Prefer": "transient"}
            return 200, {"items": [{"id": "42"}]}, {}
        if method == "GET" and path == "/record/v1/salesOrder/42":
            return (
                200,
                {"fulfillmentstatus": "partially fulfilled", "carrier": "UPS", "shipqty": "3"},
                {},
            )
        raise AssertionError(f"unexpected call: {method} {path}")

    adapter = NetSuiteAdapter()
    with (
        patch.object(NetSuiteAdapter, "_get_access_token", return_value="tok"),
        patch.object(NetSuiteAdapter, "_http", side_effect=fake_http),
    ):
        fields = adapter.fetch_status(_TARGET, "SO0001")

    assert fields == {
        "fulfillmentstatus": "partially fulfilled",
        "carrier": "UPS",
        "shipqty": "3",
    }


def test_fetch_status_returns_none_when_order_not_found() -> None:
    adapter = NetSuiteAdapter()
    with (
        patch.object(NetSuiteAdapter, "_get_access_token", return_value="tok"),
        patch.object(NetSuiteAdapter, "_http", return_value=(200, {"items": []}, {})),
    ):
        assert adapter.fetch_status(_TARGET, "SO9999") is None


def test_cancel_fails_closed_pending_account_specific_status_confirmation() -> None:
    """Never invent a native "cancelled" value: the approved mapping has no field for
    it, so cancel() must fail closed, not silently pretend to succeed or guess one."""

    def fake_http(target: Any, token: str, method: str, path: str, **kwargs: Any) -> Any:
        if method == "POST" and path == "/query/v1/suiteql":
            return 200, {"items": [{"id": "42"}]}, {}
        raise AssertionError(f"unexpected call: {method} {path}")

    adapter = NetSuiteAdapter()
    with (
        patch.object(NetSuiteAdapter, "_get_access_token", return_value="tok"),
        patch.object(NetSuiteAdapter, "_http", side_effect=fake_http),
    ):
        result = adapter.cancel(_TARGET, "SO0001")

    assert not result.success
    assert result.terminal


def test_cancel_fails_with_order_not_found_when_tranid_has_no_match() -> None:
    adapter = NetSuiteAdapter()
    with (
        patch.object(NetSuiteAdapter, "_get_access_token", return_value="tok"),
        patch.object(NetSuiteAdapter, "_http", return_value=(200, {"items": []}, {})),
    ):
        result = adapter.cancel(_TARGET, "SO9999")

    assert not result.success
    assert result.terminal
