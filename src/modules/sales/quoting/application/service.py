"""QuoteService — operator-authored quotes and subsidiaries (Q4=A, Q5=A).

The operator (distributor) issues a quote to a reseller; the reseller then places an
order against it. This service is the write side for both the subsidiary record and
quotes; price resolution for an order reads a quote through `QuoteRepository` directly
(see `ordering.application.order_service.QuoteDirectory`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.shared.types import TenantId, generate_id

from ..domain.errors import NoErpRouteConfigured
from ..domain.models import (
    EndCustomer,
    Quote,
    QuoteLine,
    QuoteStatus,
    Subsidiary,
)

if TYPE_CHECKING:
    from datetime import date

    from .ports import (
        QuoteRepository,
        SubsidiaryRepository,
        SubsidiaryRouteRepository,
    )


class QuoteService:
    def __init__(
        self,
        quotes: QuoteRepository,
        companies: SubsidiaryRepository,
        routes: SubsidiaryRouteRepository,
    ) -> None:
        self._quotes = quotes
        self._companies = companies
        self._routes = routes

    # --- subsidiary ---
    def create_subsidiary(self, *, name: str, country: str, language: str) -> Subsidiary:
        company = Subsidiary(
            subsidiary_id=generate_id("oc"), name=name, country=country, language=language
        )
        self._companies.add(company)
        return company

    def get_subsidiary(self, subsidiary_id: str) -> Subsidiary | None:
        return self._companies.get(subsidiary_id)

    def list_subsidiaries(self) -> list[Subsidiary]:
        return self._companies.list_all()

    # --- subsidiary -> ERP routing (Increment 7) ---
    def set_erp_route(
        self, subsidiary_id: str, connection_id: str, erp_company_id: str = ""
    ) -> None:
        if self._companies.get(subsidiary_id) is None:
            raise ValueError(f"unknown subsidiary '{subsidiary_id}'")
        owner = self._routes.find_by_connection(connection_id)
        if owner is not None and owner != subsidiary_id:
            raise ValueError(
                f"connection '{connection_id}' already belongs to subsidiary '{owner}'"
            )
        self._routes.set_route(subsidiary_id, connection_id, erp_company_id)

    def get_erp_route(self, subsidiary_id: str) -> str | None:
        return self._routes.get_route(subsidiary_id)

    def get_erp_company_id(self, subsidiary_id: str) -> str:
        return self._routes.get_company_id(subsidiary_id)

    def find_subsidiary(self, connection_id: str, erp_company_id: str) -> str | None:
        return self._routes.find_subsidiary(connection_id, erp_company_id)

    # --- quotes ---
    def issue_quote(
        self,
        *,
        tenant_id: TenantId,
        subsidiary_id: str,
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
        if self._companies.get(subsidiary_id) is None:
            raise ValueError(f"unknown subsidiary '{subsidiary_id}'")
        connection_id = self._routes.get_route(subsidiary_id)
        if connection_id is None:
            raise NoErpRouteConfigured(subsidiary_id)
        quote = Quote(
            quote_id=generate_id("qot"),
            tenant_id=tenant_id,
            subsidiary_id=subsidiary_id,
            end_customer=end_customer,
            currency=currency,
            valid_from=valid_from,
            valid_until=valid_until,
            routed_to_connection_id=connection_id,
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
