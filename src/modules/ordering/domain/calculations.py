"""Pure money/tax calculations over `OrderLine` (canonical-model-v2.md §3/§5).

Every function here is pure — same inputs, same output, no I/O — and deliberately
decoupled from the `Order` aggregate. Wiring these into persisted order-level fields
(shipping, order-level discount) is future-phase work, once a command/event exists to
set them; today there's no price source wired in (no catalog price lookup), so a line
with `unit_price is None` contributes nothing and callers get `None` back rather than a
silently-wrong zero.
"""

from __future__ import annotations

from decimal import Decimal

from src.shared.money import Money, TaxRate, round_money

from .models import OrderLine


def line_total(line: OrderLine) -> Money | None:
    """quantity * unit_price - line_discount, rounded. None if no price is set."""
    if line.unit_price is None:
        return None
    currency = line.unit_price.currency
    if line.line_discount is not None and line.line_discount.currency != currency:
        raise ValueError(
            f"line_discount currency {line.line_discount.currency!r} != unit_price currency {currency!r}"
        )
    discount = line.line_discount.amount if line.line_discount is not None else Decimal(0)
    gross = line.quantity * line.unit_price.amount
    return Money(round_money(gross - discount, currency), currency)


def _tax_breakdown(line: OrderLine) -> list[tuple[TaxRate, Money]]:
    total = line_total(line)
    if total is None:
        return []
    currency = total.currency
    breakdown: list[tuple[TaxRate, Money]] = []
    for tax_rate in line.tax_rates:
        if tax_rate.inclusive:
            # The rate is already inside `total` — extract it rather than add on top.
            taxable_base = total.amount / (Decimal(1) + tax_rate.rate)
            amount = total.amount - taxable_base
        else:
            amount = total.amount * tax_rate.rate
        breakdown.append((tax_rate, Money(round_money(amount, currency), currency)))
    return breakdown


def line_tax_total(line: OrderLine) -> Money | None:
    """Sum of this line's tax amounts (both inclusive-extracted and exclusive-added).
    None if no price is set — there's nothing to tax."""
    total = line_total(line)
    if total is None:
        return None
    result = Money(Decimal(0), total.currency)
    for _, amount in _tax_breakdown(line):
        result = result + amount
    return result


def line_total_with_tax(line: OrderLine) -> Money | None:
    """`line_total` plus exclusive tax only — inclusive tax is already inside `line_total`."""
    total = line_total(line)
    if total is None:
        return None
    result = total
    for tax_rate, amount in _tax_breakdown(line):
        if not tax_rate.inclusive:
            result = result + amount
    return result


def order_subtotal(lines: list[OrderLine]) -> Money | None:
    """Sum of `line_total` across priced lines. None if no line has a price.
    Raises if priced lines disagree on currency — never silently mixes currencies."""
    totals = [t for t in (line_total(line) for line in lines) if t is not None]
    return sum_money(totals)


def order_tax_total(lines: list[OrderLine]) -> Money | None:
    """Sum of `line_tax_total` across priced lines. None if no line has a price."""
    totals = [t for t in (line_tax_total(line) for line in lines) if t is not None]
    return sum_money(totals)


def sum_money(amounts: list[Money]) -> Money | None:
    """Sum a list of `Money`, None if empty. Used by order-level calculations above and
    by the projection layer (summing already-computed `line_total`s for display)."""
    if not amounts:
        return None
    currency = amounts[0].currency
    for amount in amounts:
        if amount.currency != currency:
            raise ValueError(f"order lines mix currencies: {currency!r} vs {amount.currency!r}")
    result = Money(Decimal(0), currency)
    for amount in amounts:
        result = result + amount
    return result
