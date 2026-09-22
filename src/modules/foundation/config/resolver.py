"""Config resolution (Process 5) and routing evaluation (BR-4).

`evaluate_routing` is a pure function over a list of rules and an order dict —
in partial PBT scope. It implements ordered, first-match-wins precedence with an
explicit no-match result (BR-4.1, BR-4.2).
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import ConditionOperator, RoutingCondition, RoutingRule


@dataclass(frozen=True)
class RoutingResult:
    instance_id: str | None
    matched_rule_id: str | None
    no_match: bool


NO_MATCH = RoutingResult(instance_id=None, matched_rule_id=None, no_match=True)


def _get_field(order: dict, path: str):
    """Resolve a dotted path against a nested dict; returns None if absent."""
    current = order
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _evaluate_condition(cond: RoutingCondition, order: dict) -> bool:
    actual = _get_field(order, cond.field)
    op = cond.operator
    value = cond.value
    if op == ConditionOperator.EQUALS:
        return actual == value
    if op == ConditionOperator.NOT_EQUALS:
        return actual != value
    if op == ConditionOperator.IN:
        return actual in value if isinstance(value, (list, tuple, set)) else False
    if op == ConditionOperator.CONTAINS:
        try:
            return value in actual
        except TypeError:
            return False
    if op == ConditionOperator.GT:
        try:
            return actual is not None and actual > value
        except TypeError:
            return False
    if op == ConditionOperator.LT:
        try:
            return actual is not None and actual < value
        except TypeError:
            return False
    return False


def evaluate_routing(rules: list[RoutingRule], order: dict) -> RoutingResult:
    """Ordered, first-match-wins. All conditions in a rule are ANDed (BR-4.1)."""
    for rule in sorted((r for r in rules if r.enabled), key=lambda r: r.order_index):
        if all(_evaluate_condition(c, order) for c in rule.conditions):
            return RoutingResult(instance_id=rule.target_instance_id, matched_rule_id=rule.rule_id, no_match=False)
    return NO_MATCH
