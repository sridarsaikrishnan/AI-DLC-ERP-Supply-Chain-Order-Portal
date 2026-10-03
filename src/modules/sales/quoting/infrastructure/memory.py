"""In-memory quoting repositories (tests + memory profile)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.types import TenantId

    from ..domain.models import OperatingCompany, Quote


class InMemoryQuoteRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Quote] = {}

    def add(self, quote: Quote) -> None:
        self._by_id[quote.quote_id] = quote

    def update(self, quote: Quote) -> None:
        self._by_id[quote.quote_id] = quote

    def get(self, quote_id: str) -> Quote | None:
        return self._by_id.get(quote_id)

    def list_by_tenant(self, tenant_id: TenantId) -> list[Quote]:
        return [q for q in self._by_id.values() if q.tenant_id == tenant_id]

    def list_all(self) -> list[Quote]:
        return list(self._by_id.values())


class InMemoryOperatingCompanyRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, OperatingCompany] = {}

    def add(self, company: OperatingCompany) -> None:
        self._by_id[company.operating_company_id] = company

    def get(self, operating_company_id: str) -> OperatingCompany | None:
        return self._by_id.get(operating_company_id)

    def list_all(self) -> list[OperatingCompany]:
        return list(self._by_id.values())
