from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.modules.ordering.domain.calculations import (
    line_tax_total,
    line_total,
    line_total_with_tax,
    order_grand_total,
    order_subtotal,
    order_tax_total,
)
from src.modules.ordering.domain.models import OrderLine
from src.shared.money import Money, TaxRate, round_money

# --- ordinary unit tests -----------------------------------------------------------


def _line(qty: str, price: str | None, discount: str | None = None, tax_rates: list[TaxRate] | None = None) -> OrderLine:
    return OrderLine(
        product_key="ANVIL",
        quantity=Decimal(qty),
        unit_of_measure="EA",
        unit_price=None if price is None else Money(Decimal(price), "USD"),
        line_discount=None if discount is None else Money(Decimal(discount), "USD"),
        tax_rates=tax_rates or [],
    )


def test_line_total_none_without_price() -> None:
    assert line_total(_line("2", None)) is None


def test_line_total_basic() -> None:
    assert line_total(_line("2", "10.00")) == Money(Decimal("20.00"), "USD")


def test_line_total_with_discount() -> None:
    assert line_total(_line("2", "10.00", discount="3.00")) == Money(Decimal("17.00"), "USD")


def test_line_discount_currency_mismatch_raises() -> None:
    line = OrderLine(
        product_key="X", quantity=Decimal(1), unit_of_measure="EA",
        unit_price=Money(Decimal("10"), "USD"), line_discount=Money(Decimal("1"), "EUR"),
    )
    with pytest.raises(ValueError):
        line_total(line)


def test_exclusive_tax_adds_on_top() -> None:
    line = _line("1", "100.00", tax_rates=[TaxRate("VAT", Decimal("0.20"), inclusive=False)])
    assert line_total(line) == Money(Decimal("100.00"), "USD")
    assert line_tax_total(line) == Money(Decimal("20.00"), "USD")
    assert line_total_with_tax(line) == Money(Decimal("120.00"), "USD")


def test_inclusive_tax_is_extracted_not_added() -> None:
    line = _line("1", "120.00", tax_rates=[TaxRate("VAT", Decimal("0.20"), inclusive=True)])
    assert line_total(line) == Money(Decimal("120.00"), "USD")
    assert line_tax_total(line) == Money(Decimal("20.00"), "USD")
    assert line_total_with_tax(line) == Money(Decimal("120.00"), "USD")  # tax already inside


def test_order_subtotal_none_when_no_line_priced() -> None:
    assert order_subtotal([_line("1", None), _line("2", None)]) is None


def test_order_subtotal_skips_unpriced_lines() -> None:
    lines = [_line("2", "10.00"), _line("5", None)]
    assert order_subtotal(lines) == Money(Decimal("20.00"), "USD")


def test_order_subtotal_currency_mismatch_raises() -> None:
    lines = [
        OrderLine(product_key="A", quantity=Decimal(1), unit_of_measure="EA", unit_price=Money(Decimal("10"), "USD")),
        OrderLine(product_key="B", quantity=Decimal(1), unit_of_measure="EA", unit_price=Money(Decimal("10"), "EUR")),
    ]
    with pytest.raises(ValueError):
        order_subtotal(lines)


def test_order_grand_total_with_discount_and_shipping() -> None:
    subtotal = Money(Decimal("100.00"), "USD")
    tax = Money(Decimal("20.00"), "USD")
    total = order_grand_total(subtotal, tax, discount=Money(Decimal("10.00"), "USD"), shipping=Money(Decimal("5.00"), "USD"))
    assert total == Money(Decimal("115.00"), "USD")  # 100 - 10 + 20 + 5


def test_order_tax_total_sums_lines() -> None:
    lines = [
        _line("1", "100.00", tax_rates=[TaxRate("VAT", Decimal("0.10"))]),
        _line("1", "50.00", tax_rates=[TaxRate("VAT", Decimal("0.10"))]),
    ]
    assert order_tax_total(lines) == Money(Decimal("15.00"), "USD")


# --- property-based tests -----------------------------------------------------------

quantities = st.decimals(min_value="0.01", max_value="1000", places=2)
prices = st.decimals(min_value="0.00", max_value="100000", places=2)
rates = st.decimals(min_value="0.00", max_value="0.50", places=4)


@given(qty=quantities, price=prices)
def test_line_total_is_total_and_never_raises(qty: Decimal, price: Decimal) -> None:
    result = line_total(_line(str(qty), str(price)))
    assert result is not None
    assert isinstance(result, Money)


@given(qty=quantities, price=prices)
def test_line_total_matches_round_money_of_qty_times_price(qty: Decimal, price: Decimal) -> None:
    result = line_total(_line(str(qty), str(price)))
    assert result == Money(round_money(qty * price, "USD"), "USD")


@given(qty=quantities, price=prices, rate=rates)
def test_exclusive_tax_equals_rate_times_total(qty: Decimal, price: Decimal, rate: Decimal) -> None:
    line = _line(str(qty), str(price), tax_rates=[TaxRate("T", rate, inclusive=False)])
    total = line_total(line)
    tax = line_tax_total(line)
    assert tax == Money(round_money(total.amount * rate, "USD"), "USD")  # type: ignore[union-attr]


@given(qty=quantities, price=prices, rate=rates)
def test_inclusive_tax_never_exceeds_total(qty: Decimal, price: Decimal, rate: Decimal) -> None:
    line = _line(str(qty), str(price), tax_rates=[TaxRate("T", rate, inclusive=True)])
    total = line_total(line)
    tax = line_tax_total(line)
    assert tax.amount <= total.amount  # type: ignore[union-attr]


@given(st.lists(st.tuples(quantities, prices), min_size=1, max_size=10))
def test_order_subtotal_equals_sum_of_line_totals(rows: list[tuple[Decimal, Decimal]]) -> None:
    lines = [_line(str(q), str(p)) for q, p in rows]
    expected = Money(Decimal(0), "USD")
    for line in lines:
        expected = expected + line_total(line)  # type: ignore[arg-type]
    assert order_subtotal(lines) == expected
