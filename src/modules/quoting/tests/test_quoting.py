from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.modules.quoting.application.service import QuoteService
from src.modules.quoting.domain.models import EndCustomer, QuoteLine, QuoteStatus
from src.modules.quoting.infrastructure.memory import (
    InMemoryOperatingCompanyRepository,
    InMemoryQuoteRepository,
)
from src.shared.money import Money
from src.shared.types import TenantId


def _service() -> QuoteService:
    return QuoteService(InMemoryQuoteRepository(), InMemoryOperatingCompanyRepository())


def _issue(svc: QuoteService, *, valid_from: date, valid_until: date):
    company = svc.create_operating_company(name="Dist", country="US", language="en")
    return svc.issue_quote(
        tenant_id=TenantId("tnt_a"),
        operating_company_id=company.operating_company_id,
        end_customer=EndCustomer(name="Downstream", ship_to="1 Main St"),
        currency="USD",
        valid_from=valid_from,
        valid_until=valid_until,
        lines=[QuoteLine(product_key="ANVIL", unit_price=Money(Decimal("10.00"), "USD"), unit_of_measure="EA")],
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
    company = svc.create_operating_company(name="Dist", country="US", language="en")
    with pytest.raises(ValueError):
        svc.issue_quote(
            tenant_id=TenantId("t"), operating_company_id=company.operating_company_id,
            end_customer=EndCustomer(name="x", ship_to="y"), currency="USD",
            valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31), lines=[],
        )
    with pytest.raises(ValueError):
        svc.issue_quote(
            tenant_id=TenantId("t"), operating_company_id=company.operating_company_id,
            end_customer=EndCustomer(name="x", ship_to="y"), currency="USD",
            valid_from=date(2026, 12, 31), valid_until=date(2026, 1, 1),  # until before from
            lines=[QuoteLine(product_key="A", unit_price=Money(Decimal("1"), "USD"))],
        )


def test_issue_quote_rejects_unknown_operating_company() -> None:
    svc = _service()
    with pytest.raises(ValueError):
        svc.issue_quote(
            tenant_id=TenantId("t"), operating_company_id="oc_missing",
            end_customer=EndCustomer(name="x", ship_to="y"), currency="USD",
            valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31),
            lines=[QuoteLine(product_key="A", unit_price=Money(Decimal("1"), "USD"))],
        )


def test_find_line_matches_by_product_key() -> None:
    svc = _service()
    quote = _issue(svc, valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31))
    assert quote.find_line("ANVIL") is not None
    assert quote.find_line("NOPE") is None
