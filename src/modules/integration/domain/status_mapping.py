"""Native-ERP-status -> canonical-status mapping, as a registry (a PBT target).

To add a new ERP's status mapping: write one pure function `(fields: dict[str, str]) ->
CanonicalStatus | None` that reads whatever keys that ERP's status actually arrives in.
The signature doesn't force an arity — Odoo reads 2 keys (`state`, `invoice_status`), a
single-status-string ERP reads 1 (`status`), a hypothetical 3-field ERP reads 3. Add one
line to `STATUS_MAPPERS`. No other file changes. `map_native_status` itself never needs to
change again — this replaced an earlier version that hardcoded exactly 2 positional
string arguments, which was Odoo's shape leaking into what was meant to be ERP-neutral.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum


class CanonicalStatus(str, Enum):
    """Canonical lifecycle statuses an ERP poll/webhook can drive. Increment 5 removed
    `FULFILLED` (FR-A6): "fully delivered" is a shipped/delivered fact tracked via
    Fulfillment records, not a lifecycle status an ERP status string advances."""

    CONFIRMED = "CONFIRMED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


# Inputs are already lowercased/stripped by `map_native_status` before the mapper sees them.
StatusMapper = Callable[[dict[str, str]], "CanonicalStatus | None"]


def _map_odoo(fields: dict[str, str]) -> CanonicalStatus | None:
    native = fields.get("state", "")
    invoice = fields.get("invoice_status", "")
    if native == "cancel":
        return CanonicalStatus.CANCELLED
    if invoice == "invoiced":
        return CanonicalStatus.CLOSED
    # Both "sale" (confirmed) and "done" (locked/fully delivered) map to CONFIRMED now —
    # delivery is tracked as a fact via Fulfillment records, not this status (FR-A6).
    if native in ("sale", "done"):
        return CanonicalStatus.CONFIRMED
    return None


# The one place a new ERP's status mapping is registered. Keyed by the same string an
# `ErpConnection.erp_type`/`ErpTarget.erp_type` carries (upper-cased).
STATUS_MAPPERS: dict[str, StatusMapper] = {
    "ODOO": _map_odoo,
}


def map_native_status(erp_type: str, fields: dict[str, str] | None) -> CanonicalStatus | None:
    mapper = STATUS_MAPPERS.get((erp_type or "").upper())
    if mapper is None:
        return None
    clean = {k: (v or "").strip().lower() for k, v in (fields or {}).items()}
    return mapper(clean)
