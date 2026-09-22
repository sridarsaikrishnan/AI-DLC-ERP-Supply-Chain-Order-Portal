"""Config repositories (LC-U4-2). Platform-scoped CRUD (not tenant-filtered)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..foundation.persistence.tables import (
    ErpInstanceRow,
    MappingDefinitionRow,
    RoutingRuleRow,
)


class InstanceRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, row: ErpInstanceRow) -> None:
        self.session.merge(row)
        self.session.flush()

    def get(self, instance_id: str) -> ErpInstanceRow | None:
        return self.session.get(ErpInstanceRow, instance_id)

    def all(self) -> list[ErpInstanceRow]:
        return list(self.session.execute(select(ErpInstanceRow)).scalars().all())


class RoutingRuleRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, row: RoutingRuleRow) -> None:
        self.session.merge(row)
        self.session.flush()

    def get(self, rule_id: str) -> RoutingRuleRow | None:
        return self.session.get(RoutingRuleRow, rule_id)

    def ordered(self) -> list[RoutingRuleRow]:
        return list(
            self.session.execute(select(RoutingRuleRow).order_by(RoutingRuleRow.order_index)).scalars().all()
        )


class MappingRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, row: MappingDefinitionRow) -> None:
        self.session.merge(row)
        self.session.flush()

    def all(self) -> list[MappingDefinitionRow]:
        return list(self.session.execute(select(MappingDefinitionRow)).scalars().all())
