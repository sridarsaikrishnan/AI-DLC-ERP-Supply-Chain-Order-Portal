"""Money as a value object — never a float.

Binary float can't represent `0.1` exactly; errors compound once tax/discount math is
layered on top. `round_money` is the one place rounding happens — every ERP adapter and
calculation uses this, not its own rounding.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

# Currencies whose minor unit isn't 2 decimal places. Not exhaustive — add one here if an
# ERP integration needs it; a currency missing from this map defaults to 2.
_MINOR_UNIT_OVERRIDES: dict[str, int] = {
    "JPY": 0,
    "KRW": 0,
    "VND": 0,
    "BHD": 3,
    "KWD": 3,
    "OMR": 3,
    "JOD": 3,
}


def minor_units(currency: str) -> int:
    return _MINOR_UNIT_OVERRIDES.get(currency.upper(), 2)


def round_money(amount: Decimal, currency: str) -> Decimal:
    digits = minor_units(currency)
    quantum = Decimal(1).scaleb(-digits)
    return amount.quantize(quantum, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        amount = self.amount if isinstance(self.amount, Decimal) else Decimal(str(self.amount))
        object.__setattr__(self, "amount", round_money(amount, self.currency))

    def __add__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def _require_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"currency mismatch: {self.currency} vs {other.currency}")


def money_to_payload(money: Money | None) -> dict[str, str] | None:
    """JSON-safe form for an event/snapshot payload (JSONB can't hold Decimal)."""
    return None if money is None else {"amount": str(money.amount), "currency": money.currency}


def money_from_payload(data: dict[str, Any] | None) -> Money | None:
    return None if data is None else Money(Decimal(data["amount"]), data["currency"])


@dataclass(frozen=True)
class TaxRate:
    """A tax to apply to a line: `inclusive=True` means the rate is already baked into
    the line's price (extract it), `False` means it's added on top."""

    code: str
    rate: Decimal
    inclusive: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.rate, Decimal):
            object.__setattr__(self, "rate", Decimal(str(self.rate)))


def tax_rate_to_payload(tax_rate: TaxRate) -> dict[str, Any]:
    return {"code": tax_rate.code, "rate": str(tax_rate.rate), "inclusive": tax_rate.inclusive}


def tax_rate_from_payload(data: dict[str, Any]) -> TaxRate:
    return TaxRate(
        code=data["code"], rate=data["rate"], inclusive=bool(data.get("inclusive", False))
    )
