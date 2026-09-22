"""RoutingService (LC-U3-4). Loads routing rules from U0 config and evaluates them.

Delegates precedence logic to U0's pure `evaluate_routing`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..foundation.config.models import (
    ConditionOperator,
    RoutingCondition,
    RoutingRule,
)
from ..foundation.config.resolver import RoutingResult, evaluate_routing
from ..foundation.persistence.tables import RoutingRuleRow


def _row_to_rule(row: RoutingRuleRow) -> RoutingRule:
    conditions = [
        RoutingCondition(
            field=c["field"],
            operator=ConditionOperator(c["operator"]),
            value=c["value"],
        )
        for c in (row.conditions or [])
    ]
    return RoutingRule(
        rule_id=row.id,
        order_index=row.order_index,
        conditions=conditions,
        target_instance_id=row.target_instance_id,
        enabled=row.enabled,
    )


class RoutingService:
    def __init__(self, session: Session):
        self.session = session

    def load_rules(self) -> list[RoutingRule]:
        rows = list(self.session.execute(select(RoutingRuleRow)).scalars().all())
        return [_row_to_rule(r) for r in rows]

    def route(self, order: dict) -> RoutingResult:
        return evaluate_routing(self.load_rules(), order)
