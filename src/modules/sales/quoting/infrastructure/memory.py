"""In-memory quoting repositories (tests + memory profile)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.types import TenantId

    from ..domain.models import Quote, Subsidiary


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


class InMemorySubsidiaryRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Subsidiary] = {}

    def add(self, company: Subsidiary) -> None:
        self._by_id[company.subsidiary_id] = company

    def get(self, subsidiary_id: str) -> Subsidiary | None:
        return self._by_id.get(subsidiary_id)

    def list_all(self) -> list[Subsidiary]:
        return list(self._by_id.values())


class InMemorySubsidiaryRouteRepository:
    def __init__(self) -> None:
        self._route_by_company: dict[str, str] = {}

    def set_route(self, subsidiary_id: str, connection_id: str) -> None:
        self._route_by_company[subsidiary_id] = connection_id

    def get_route(self, subsidiary_id: str) -> str | None:
        return self._route_by_company.get(subsidiary_id)
