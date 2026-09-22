"""Unit tests for routing evaluation (BR-4.1, BR-4.2)."""

from src.modules.foundation.config.models import (
    ConditionOperator,
    RoutingCondition,
    RoutingRule,
)
from src.modules.foundation.config.resolver import evaluate_routing


def _rule(rule_id, idx, field, op, value, target, enabled=True):
    return RoutingRule(
        rule_id=rule_id,
        order_index=idx,
        conditions=[RoutingCondition(field=field, operator=op, value=value)],
        target_instance_id=target,
        enabled=enabled,
    )


def test_first_match_wins_by_order_index():
    rules = [
        _rule("r2", 2, "ship_to.region", ConditionOperator.EQUALS, "EU", "odoo-eu"),
        _rule("r1", 1, "ship_to.region", ConditionOperator.EQUALS, "EU", "erpnext-eu"),
    ]
    result = evaluate_routing(rules, {"ship_to": {"region": "EU"}})
    assert result.instance_id == "erpnext-eu"  # lower order_index wins


def test_no_match_returns_no_match():
    rules = [_rule("r1", 1, "ship_to.region", ConditionOperator.EQUALS, "EU", "odoo-eu")]
    result = evaluate_routing(rules, {"ship_to": {"region": "US"}})
    assert result.no_match is True
    assert result.instance_id is None


def test_disabled_rule_is_skipped():
    rules = [_rule("r1", 1, "ship_to.region", ConditionOperator.EQUALS, "EU", "odoo-eu", enabled=False)]
    result = evaluate_routing(rules, {"ship_to": {"region": "EU"}})
    assert result.no_match is True


def test_in_operator():
    rules = [_rule("r1", 1, "currency", ConditionOperator.IN, ["USD", "EUR"], "odoo")]
    assert evaluate_routing(rules, {"currency": "EUR"}).instance_id == "odoo"
    assert evaluate_routing(rules, {"currency": "GBP"}).no_match is True
