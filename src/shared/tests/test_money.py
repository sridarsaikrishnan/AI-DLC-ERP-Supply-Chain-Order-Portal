from __future__ import annotations

from decimal import Decimal

from src.shared.money import Money, round_money


def test_round_money_default_two_decimals() -> None:
    assert round_money(Decimal("2.005"), "USD") == Decimal("2.01")  # ROUND_HALF_UP


def test_round_money_zero_decimal_currency() -> None:
    assert round_money(Decimal("100.6"), "JPY") == Decimal("101")


def test_money_rounds_on_construction_not_just_in_round_money() -> None:
    assert Money(Decimal("2.005"), "USD").amount == Decimal("2.01")


def test_money_add_requires_same_currency() -> None:
    assert (Money(Decimal("1.50"), "USD") + Money(Decimal("2.25"), "USD")).amount == Decimal("3.75")
    try:
        Money(Decimal("1"), "USD") + Money(Decimal("1"), "EUR")
    except ValueError:
        pass
    else:
        raise AssertionError("expected currency mismatch to raise")


def test_money_never_built_from_float_imprecision() -> None:
    # str(x) first — Decimal(0.1) directly would carry float's binary-repr noise.
    assert Money(0.1, "USD").amount == Decimal("0.10")
