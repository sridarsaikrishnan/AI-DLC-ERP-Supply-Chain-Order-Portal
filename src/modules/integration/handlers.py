"""Job handlers (LC-U3-5, Processes 1-3).

Registered into U0's HandlerRegistry. Each handler runs inside the U0 WorkerHost
transaction with a SecurityContext already bound from the job's tenant id.

Transient failures raise (U0 applies bounded retry); terminal failures mark the
order Failed. Idempotency is guaranteed by U0's dedupe_key check before the handler
performs side effects.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..foundation.config.models import DataType, Direction, ErpType, MappingDefinition
from ..foundation.config.models import MappingEntry
from ..foundation.persistence.tables import (
    ErpInstanceRow,
    MappingDefinitionRow,
    OrderRow,
    OrderStatusHistoryRow,
)
from ...shared.logging import get_logger
from .adapter import AdapterAction, AdapterRegistry
from .mapping_engine import to_erp
from .routing_service import RoutingService

logger = get_logger("integration.handlers")

# Native ERP status -> canonical lifecycle state (default reconciliation map).
_NATIVE_TO_CANONICAL = {
    "Accepted": "Accepted",
    "Processing": "Processing",
    "Shipped": "Shipped",
    "Invoiced": "Invoiced",
    "Cancelled": "Cancelled",
}


class TransientError(Exception):
    """Raised to signal U0 to retry the job."""


def _record_status(session: Session, order: OrderRow, state: str, reason: str | None = None, erp_ref: str | None = None) -> None:
    order.lifecycle_state = state
    if erp_ref:
        order.erp_reference = erp_ref
    session.add(
        OrderStatusHistoryRow(
            id=str(uuid.uuid4()),
            order_id=order.id,
            tenant_id=order.tenant_id,
            state=state,
            reason=reason,
            occurred_at=datetime.now(timezone.utc),
        )
    )
    session.flush()


def _load_mapping(session: Session, instance_id: str, data_type: DataType, direction: Direction) -> MappingDefinition | None:
    row = (
        session.query(MappingDefinitionRow)
        .filter_by(instance_id=instance_id, data_type=data_type.value, direction=direction.value)
        .first()
    )
    if row is None:
        return None
    return MappingDefinition(
        mapping_id=row.id,
        instance_id=row.instance_id,
        data_type=DataType(row.data_type),
        direction=Direction(row.direction),
        field_entries=[MappingEntry(**e) for e in (row.field_entries or [])],
        expressions=[],
    )


def make_handlers(registry: AdapterRegistry):
    """Factory binding the adapter registry into the handler closures."""

    def _adapter_for(session: Session, instance_id: str):
        instance = session.get(ErpInstanceRow, instance_id)
        if instance is None or instance.status != "active":
            return None, None
        adapter = registry.get(ErpType(instance.erp_type))
        return adapter, instance

    def process_submission(session: Session, payload: dict) -> None:
        order = session.get(OrderRow, payload["order_id"])
        if order is None:
            logger.error("order not found", extra={"extra_fields": {"order_id": payload.get("order_id")}})
            return
        # Route (BR-U3-1) using the stored canonical payload
        result = RoutingService(session).route(order.payload)
        if result.no_match:
            _record_status(session, order, "Failed", reason="no route matched")
            return
        adapter, instance = _adapter_for(session, result.instance_id)
        if adapter is None:
            _record_status(session, order, "Failed", reason="target instance unavailable")
            return
        mapping = _load_mapping(session, instance.id, DataType.SALES_ORDER, Direction.TO_ERP)
        erp_payload = to_erp(order.payload, mapping) if mapping else dict(order.payload)
        res = adapter.submit(erp_payload, instance.connection_ref)
        if res.success:
            _record_status(session, order, "Accepted", erp_ref=res.erp_reference)
        elif res.terminal:
            _record_status(session, order, "Failed", reason=res.error)
        else:
            raise TransientError(res.error or "transient submit failure")

    def process_status_sync(session: Session, payload: dict) -> None:
        order = session.get(OrderRow, payload["order_id"])
        if order is None or not order.erp_reference:
            return
        # find the instance via the last routing (stored on payload or re-route)
        result = RoutingService(session).route(order.payload)
        if result.no_match:
            return
        adapter, instance = _adapter_for(session, result.instance_id)
        if adapter is None:
            return
        res = adapter.fetch_status(order.erp_reference, instance.connection_ref)
        if res.success and res.native_status:
            canonical = _NATIVE_TO_CANONICAL.get(res.native_status, order.lifecycle_state)
            if canonical != order.lifecycle_state:
                _record_status(session, order, canonical, erp_ref=order.erp_reference)

    def process_corrective_action(session: Session, payload: dict) -> None:
        order = session.get(OrderRow, payload["order_id"])
        if order is None:
            return
        action = AdapterAction(payload["action"])
        if action == AdapterAction.RESUBMIT:
            process_submission(session, {"order_id": order.id})
            return
        if not order.erp_reference:
            _record_status(session, order, "Failed", reason="no erp reference for corrective action")
            return
        result = RoutingService(session).route(order.payload)
        adapter, instance = _adapter_for(session, result.instance_id) if not result.no_match else (None, None)
        if adapter is None:
            _record_status(session, order, order.lifecycle_state, reason="instance unavailable for corrective action")
            return
        res = adapter.send_corrective_action(action, order.erp_reference, instance.connection_ref, payload.get("amended_payload"))
        if res.success:
            new_state = "Cancelled" if action == AdapterAction.CANCEL else "Amended"
            _record_status(session, order, new_state, erp_ref=order.erp_reference)
        elif res.terminal:
            # surface reason, preserve prior state (BR-U3-3)
            _record_status(session, order, order.lifecycle_state, reason=res.error)
        else:
            raise TransientError(res.error or "transient corrective failure")

    return {
        "process_submission": process_submission,
        "process_status_sync": process_status_sync,
        "process_corrective_action": process_corrective_action,
    }
