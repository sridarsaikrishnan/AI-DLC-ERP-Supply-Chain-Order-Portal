"""QuoteService — operator-authored quotes and operating companies (Q4=A, Q5=A).

The operator (distributor) issues a quote to a reseller; the reseller then places an
order against it. This service is the write side for both the office card and quotes;
price resolution for an order reads a quote through `QuoteRepository` directly (see
`ordering.application.order_service.QuoteDirectory`).
"""

from __future__ import annotations

from datetime import date

from src.shared.types import TenantId, generate_id

from ..domain.models import (
    EndCustomer,
    OperatingCompany,
    Quote,
    QuoteLine,
    QuoteStatus,
)
from .ports import OperatingCompanyRepository, QuoteRepository


class QuoteService:
    def __init__(self, quotes: QuoteRepository, companies: OperatingCompanyRepository) -> None:
        self._quotes = quotes
        self._companies = companies

    # --- operating company (office card) ---
    def create_operating_company(self, *, name: str, country: str, language: str) -> OperatingCompany:
        company = OperatingCompany(
            operating_company_id=generate_id("oc"), name=name, country=country, language=language
        )
        self._companies.add(company)
        return company

    def get_operating_company(self, operating_company_id: str) -> OperatingCompany | None:
        return self._companies.get(operating_company_id)

    def list_operating_companies(self) -> list[OperatingCompany]:
        return self._companies.list_all()

    # --- quotes ---
    def issue_quote(
        self,
        *,
        tenant_id: TenantId,
        operating_company_id: str,
        end_customer: EndCustomer,
        currency: str,
        valid_from: date,
        valid_until: date,
        lines: list[QuoteLine],
    ) -> Quote:
        if not lines:
            raise ValueError("a quote must have at least one line")
        if valid_until < valid_from:
            raise ValueError("valid_until must not precede valid_from")
        if self._companies.get(operating_company_id) is None:
            raise ValueError(f"unknown operating company '{operating_company_id}'")
        quote = Quote(
            quote_id=generate_id("qot"),
            tenant_id=tenant_id,
            operating_company_id=operating_company_id,
            end_customer=end_customer,
            currency=currency,
            valid_from=valid_from,
            valid_until=valid_until,
            lines=list(lines),
            status=QuoteStatus.ISSUED,
        )
        self._quotes.add(quote)
        return quote

    def get_quote(self, quote_id: str) -> Quote | None:
        return self._quotes.get(quote_id)

    def list_quotes_for_tenant(self, tenant_id: TenantId) -> list[Quote]:
        return self._quotes.list_by_tenant(tenant_id)

    def list_quotes(self) -> list[Quote]:
        return self._quotes.list_all()

    def mark_accepted(self, quote_id: str) -> None:
        quote = self._quotes.get(quote_id)
        if quote is None or quote.status is QuoteStatus.ACCEPTED:
            return
        quote.status = QuoteStatus.ACCEPTED
        self._quotes.update(quote)
