from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.modules.sales.quoting.application.service import QuoteService
from src.modules.sales.quoting.domain.errors import NoErpRouteConfigured
from src.modules.sales.quoting.domain.models import EndCustomer, QuoteLine, QuoteStatus
from src.modules.sales.quoting.infrastructure.memory import (
    InMemoryQuoteRepository,
    InMemorySubsidiaryRepository,
    InMemorySubsidiaryRouteRepository,
)
from src.shared.money import Money
from src.shared.types import TenantId


def _service() -> QuoteService:
    return QuoteService(
        InMemoryQuoteRepository(),
        InMemorySubsidiaryRepository(),
        InMemorySubsidiaryRouteRepository(),
    )


def _issue(svc: QuoteService, *, valid_from: date, valid_until: date):
    company = svc.create_subsidiary(name="Dist", country="US", language="en")
    svc.set_erp_route(company.subsidiary_id, "conn_odoo_us")
    return svc.issue_quote(
        tenant_id=TenantId("tnt_a"),
        subsidiary_id=company.subsidiary_id,
        end_customer=EndCustomer(name="Downstream", ship_to="1 Main St"),
        currency="USD",
        valid_from=valid_from,
        valid_until=valid_until,
        lines=[
            QuoteLine(
                product_key="ANVIL", unit_price=Money(Decimal("10.00"), "USD"), unit_of_measure="EA"
            )
        ],
    )


def test_issued_quote_is_valid_inside_its_window() -> None:
    svc = _service()
    quote = _issue(svc, valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31))
    assert quote.status is QuoteStatus.ISSUED
    assert quote.is_valid_on(date(2026, 6, 1))
    assert not quote.is_valid_on(date(2025, 12, 31))  # before window
    assert not quote.is_valid_on(date(2027, 1, 1))  # after window


def test_expired_or_accepted_quote_cannot_price_even_in_window() -> None:
    svc = _service()
    quote = _issue(svc, valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31))
    quote.status = QuoteStatus.ACCEPTED
    assert not quote.is_valid_on(date(2026, 6, 1))  # only ISSUED quotes price an order


def test_issue_quote_rejects_empty_lines_and_bad_window() -> None:
    svc = _service()
    company = svc.create_subsidiary(name="Dist", country="US", language="en")
    with pytest.raises(ValueError):
        svc.issue_quote(
            tenant_id=TenantId("t"),
            subsidiary_id=company.subsidiary_id,
            end_customer=EndCustomer(name="x", ship_to="y"),
            currency="USD",
            valid_from=date(2026, 1, 1),
            valid_until=date(2026, 12, 31),
            lines=[],
        )
    with pytest.raises(ValueError):
        svc.issue_quote(
            tenant_id=TenantId("t"),
            subsidiary_id=company.subsidiary_id,
            end_customer=EndCustomer(name="x", ship_to="y"),
            currency="USD",
            valid_from=date(2026, 12, 31),
            valid_until=date(2026, 1, 1),  # until before from
            lines=[QuoteLine(product_key="A", unit_price=Money(Decimal("1"), "USD"))],
        )


def test_issue_quote_rejects_unknown_subsidiary() -> None:
    svc = _service()
    with pytest.raises(ValueError):
        svc.issue_quote(
            tenant_id=TenantId("t"),
            subsidiary_id="oc_missing",
            end_customer=EndCustomer(name="x", ship_to="y"),
            currency="USD",
            valid_from=date(2026, 1, 1),
            valid_until=date(2026, 12, 31),
            lines=[QuoteLine(product_key="A", unit_price=Money(Decimal("1"), "USD"))],
        )


def test_find_line_matches_by_product_key() -> None:
    svc = _service()
    quote = _issue(svc, valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31))
    assert quote.find_line("ANVIL") is not None
    assert quote.find_line("NOPE") is None


def test_issue_quote_refuses_when_office_has_no_erp_route() -> None:
    svc = _service()
    company = svc.create_subsidiary(name="Dist", country="US", language="en")
    with pytest.raises(NoErpRouteConfigured):
        svc.issue_quote(
            tenant_id=TenantId("tnt_a"),
            subsidiary_id=company.subsidiary_id,
            end_customer=EndCustomer(name="x", ship_to="y"),
            currency="USD",
            valid_from=date(2026, 1, 1),
            valid_until=date(2026, 12, 31),
            lines=[QuoteLine(product_key="ANVIL", unit_price=Money(Decimal("10"), "USD"))],
        )


def test_quote_stamps_the_offices_current_erp_route() -> None:
    svc = _service()
    quote = _issue(svc, valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31))
    assert quote.routed_to_connection_id == "conn_odoo_us"

    svc.set_erp_route(quote.subsidiary_id, "conn_odoo_eu")
    assert svc.get_erp_route(quote.subsidiary_id) == "conn_odoo_eu"
    assert quote.routed_to_connection_id == "conn_odoo_us"


def test_one_odoo_belongs_to_one_subsidiary() -> None:
    svc = _service()
    company = svc.create_subsidiary(name="Dist", country="US", language="en")
    other = svc.create_subsidiary(name="Other", country="DE", language="de")
    svc.set_erp_route(company.subsidiary_id, "conn_odoo", "1")

    assert svc.find_subsidiary("conn_odoo", "1") == company.subsidiary_id
    with pytest.raises(ValueError, match="already belongs"):
        svc.set_erp_route(other.subsidiary_id, "conn_odoo", "2")
