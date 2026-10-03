"""Quoting domain errors."""

from __future__ import annotations


class QuoteNotFound(Exception):
    """No quote on file for this id/reseller — an order cannot reply to a quote that
    isn't there (FR-B2)."""


class QuoteNotValid(Exception):
    """The quote exists but isn't ISSUED-and-in-window today, so its prices no longer
    hold (FR-B1)."""


class PriceNotQuoted(Exception):
    """An ordered line has no matching priced line on the quote — refused (FR-B3)."""

    def __init__(self, product_key: str) -> None:
        super().__init__(f"no quoted price on file for '{product_key}'")
        self.product_key = product_key
