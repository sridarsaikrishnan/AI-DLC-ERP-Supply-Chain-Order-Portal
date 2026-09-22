"""OrderService (LC-U2-1). Place orders, reads, and corrective initiation.

Writes are command-then-async: validate + persist + enqueue, fulfillment by U3.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..foundation.canonical.models import CanonicalSalesOrder
from ..foundation.canonical.validator import validate_sales_order
from ..foundation.context.security_context import SecurityContext, get_context, set_context
from ..foundation.persistence.tables import OrderRow
from ..foundation.queue.job_store import JobStore
from ..foundation.queue.models import Job, JobType
from ...shared.correlation import get_correlation_id
from ...shared.errors import ValidationError, NotFoundError, PortalError
from .repositories import OrderRepository, StatusHistoryRepository

_TERMINAL = {"Cancelled", "Invoiced"}


class OrderService:
    def __init__(self, session: Session, ctx: SecurityContext | None = None):
        # Bind the context on THIS thread (FastAPI runs sync endpoints in a threadpool,
        # so the ContextVar set during dependency resolution is not visible here).
        if ctx is not None:
            set_context(ctx)
        self.session = session
        self.orders = OrderRepository(session)
        self.history = StatusHistoryRepository(session)
        self.jobs = JobStore(session)

    def _tenant_id(self) -> str:
        ctx = get_context()
        if ctx is None:
            from ...shared.errors import AuthorizationError
            raise AuthorizationError("no security context")
        return ctx.tenant_id

    def place_order(self, req_dict: dict) -> OrderRow:
        tenant_id = self._tenant_id()
        canonical = CanonicalSalesOrder(tenant_id=tenant_id, **req_dict)
        errors = validate_sales_order(canonical)
        if errors:
            raise ValidationError(errors)

        order_id = str(uuid.uuid4())
        row = OrderRow(
            id=order_id,
            tenant_id=tenant_id,
            client_reference=canonical.client_reference,
            payload=canonical.model_dump(mode="json"),
            lifecycle_state="Submitted",
        )
        self.orders.create(row)
        self.jobs.enqueue(
            Job(
                type=JobType.SUBMISSION,
                payload={"order_id": order_id},
                tenant_id=tenant_id,
                dedupe_key=f"submit:{order_id}",
                correlation_id=get_correlation_id(),
            )
        )
        return row

    def get_order(self, order_id: str) -> OrderRow:
        return self.orders.get(order_id)  # fail-closed + not-found for cross-tenant

    def list_orders(self) -> list[OrderRow]:
        return self.orders.list()

    def get_history(self, order_id: str):
        self.orders.get(order_id)  # ensures tenant ownership / existence
        return self.history.for_order(order_id)

    def initiate_corrective(self, order_id: str, action: str, amended: dict | None = None) -> None:
        order = self.orders.get(order_id)
        state = order.lifecycle_state
        action = action.upper()

        if action == "RESUBMIT" and state != "Failed":
            raise PortalError("resubmit only allowed from Failed state")
        if action in ("CANCEL", "AMEND") and state in _TERMINAL:
            raise PortalError(f"cannot {action.lower()} an order in state {state}")

        payload: dict = {"order_id": order_id, "action": action}
        if action == "AMEND":
            if amended is None:
                raise PortalError("amend requires an amended order body")
            canonical = CanonicalSalesOrder(tenant_id=order.tenant_id, **amended)
            errors = validate_sales_order(canonical)
            if errors:
                raise ValidationError(errors)
            order.payload = canonical.model_dump(mode="json")  # stage the amended canonical
            payload["amended_payload"] = order.payload

        self.jobs.enqueue(
            Job(
                type=JobType.CORRECTIVE_ACTION,
                payload=payload,
                tenant_id=order.tenant_id,
                dedupe_key=f"{action.lower()}:{order_id}:{datetime.now(timezone.utc).timestamp()}",
                correlation_id=get_correlation_id(),
            )
        )
