"""Quoting domain model (Increment 5, FR-B / FR-C).

A Quote sits in front of the Order and is the thing that makes this a distributor tool:
it names the reseller it is for, the items and their prices, how long those prices hold
(the validity window), and where the goods should go (the end customer + ship-to). The
Order is a reply to a quote; a price with no quote on file is refused (see
`ordering.application.order_service`).

CRUD, not event-sourced (ADR-0002 keeps event sourcing to the Order). Reseller-safe by
construction: a Quote carries no ERP identity — `erp_customer_id` stays on the binding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from src.shared.money import Money, TaxRate
from src.shared.types import TenantId


class QuoteStatus(str, Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"      # live: an order can be placed against it while in its window
    EXPIRED = "EXPIRED"
    ACCEPTED = "ACCEPTED"  # an order has been placed against it


@dataclass(frozen=True)
class EndCustomer:
    """The party the goods are for (FR-C2). A name and a ship-to on the quote — not a
    managed account; just these two fields."""

    name: str
    ship_to: str


@dataclass(frozen=True)
class QuoteLine:
    product_key: str
    unit_price: Money
    unit_of_measure: str = ""
    tax_rate: TaxRate | None = None
    line_discount: Money | None = None


@dataclass
class Quote:
    quote_id: str
    tenant_id: TenantId                 # the reseller this quote is for (FR-B1)
    operating_company_id: str           # which operating company issued it (FR-C3)
    end_customer: EndCustomer
    currency: str
    valid_from: date
    valid_until: date
    lines: list[QuoteLine] = field(default_factory=list)
    status: QuoteStatus = QuoteStatus.DRAFT

    def is_valid_on(self, on: date) -> bool:
        """"How long the prices hold" — the quote must be ISSUED and `on` within its
        window. EXPIRED/DRAFT/ACCEPTED quotes cannot price a new order."""
        return self.status is QuoteStatus.ISSUED and self.valid_from <= on <= self.valid_until

    def find_line(self, product_key: str) -> QuoteLine | None:
        for line in self.lines:
            if line.product_key == product_key:
                return line
        return None


@dataclass
class OperatingCompany:
    """The "office card" (FR-C3): the company you are. Country and language live here so
    document numbers and email locale have a home. A plain record, not a profile service."""

    operating_company_id: str
    name: str
    country: str
    language: str
