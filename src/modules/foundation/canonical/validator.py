"""Canonical validation (Process 1, BR-1). Pure functions — in partial PBT scope.

Collects ALL violations rather than stopping at the first.
"""

from __future__ import annotations

from datetime import date

from .models import (
    CanonicalOrderLine,
    CanonicalOrderStatus,
    CanonicalSalesOrder,
    LifecycleState,
)

# States at which an ERP reference is required (BR-1.3).
_ERP_REF_REQUIRED = {
    LifecycleState.ACCEPTED,
    LifecycleState.PROCESSING,
    LifecycleState.SHIPPED,
    LifecycleState.INVOICED,
}


def _error(path: str, message: str) -> dict:
    return {"path": path, "message": message}


def validate_sales_order(order: CanonicalSalesOrder, today: date | None = None) -> list[dict]:
    """Validate a canonical sales order (BR-1.1, BR-1.2). Returns list of errors (empty = valid)."""
    today = today or date.today()
    errors: list[dict] = []

    if not order.tenant_id:
        errors.append(_error("tenant_id", "tenant_id is required"))
    if not order.client_reference or not order.client_reference.strip():
        errors.append(_error("client_reference", "client_reference is required"))
    if not order.line_items:
        errors.append(_error("line_items", "at least one line item is required"))
    if not order.currency or len(order.currency) != 3:
        errors.append(_error("currency", "currency must be a 3-letter ISO code"))

    ship_to = order.ship_to
    if ship_to is not None:
        if not ship_to.name:
            errors.append(_error("ship_to.name", "ship-to name is required"))
        if not ship_to.lines:
            errors.append(_error("ship_to.lines", "at least one address line is required"))
        if not ship_to.city:
            errors.append(_error("ship_to.city", "ship-to city is required"))
        if not ship_to.country:
            errors.append(_error("ship_to.country", "ship-to country is required"))

    for idx, line in enumerate(order.line_items):
        errors.extend(_validate_line(line, idx, today))

    return errors


def _validate_line(line: CanonicalOrderLine, idx: int, today: date) -> list[dict]:
    errors: list[dict] = []
    prefix = f"line_items[{idx}]"
    if not line.product_key:
        errors.append(_error(f"{prefix}.product_key", "product_key is required"))
    if line.quantity is None or line.quantity <= 0:
        errors.append(_error(f"{prefix}.quantity", "quantity must be greater than 0"))
    if not line.unit_of_measure:
        errors.append(_error(f"{prefix}.unit_of_measure", "unit_of_measure is required"))
    if line.requested_date is not None and line.requested_date < today:
        errors.append(_error(f"{prefix}.requested_date", "requested_date cannot be in the past"))
    return errors


def validate_order_status(status: CanonicalOrderStatus) -> list[dict]:
    """Validate a canonical order status update (BR-1.3)."""
    errors: list[dict] = []
    if not isinstance(status.state, LifecycleState):
        errors.append(_error("state", "state must be a valid lifecycle state"))
    if status.occurred_at is None:
        errors.append(_error("occurred_at", "occurred_at is required"))
    if status.state in _ERP_REF_REQUIRED and not status.erp_reference:
        errors.append(
            _error("erp_reference", f"erp_reference is required once state is {status.state.value}")
        )
    return errors
