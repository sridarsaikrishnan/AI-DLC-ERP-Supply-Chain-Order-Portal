"""Native-ERP-status -> canonical-status mapping, as a registry (a PBT target).

To add a new ERP's status mapping: write one pure function
`(native_status: str, invoice_status: str) -> CanonicalStatus | None` (lowercased,
stripped inputs — see `_map_odoo` for the shape) and add one line to `STATUS_MAPPERS`.
No other file changes. `map_native_status` itself never needs to change again.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum


class CanonicalStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    FULFILLED = "FULFILLED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


# (native_status, invoice_status) -> canonical status, or None for "no transition".
# Both inputs are already lowercased/stripped by `map_native_status` before the mapper sees them.
StatusMapper = Callable[[str, str], "CanonicalStatus | None"]


def _map_odoo(native: str, invoice: str) -> CanonicalStatus | None:
    if native == "cancel":
        return CanonicalStatus.CANCELLED
    if invoice == "invoiced":
        return CanonicalStatus.CLOSED
    if native == "done":
        return CanonicalStatus.FULFILLED
    if native == "sale":
        return CanonicalStatus.CONFIRMED
    return None


# The one place a new ERP's status mapping is registered. Keyed by the same string an
# `ErpConnection.erp_type`/`ErpTarget.erp_type` carries (upper-cased).
STATUS_MAPPERS: dict[str, StatusMapper] = {
    "ODOO": _map_odoo,
}


def map_native_status(
    erp_type: str, native_status: str | None, invoice_status: str | None = None
) -> CanonicalStatus | None:
    mapper = STATUS_MAPPERS.get((erp_type or "").upper())
    if mapper is None:
        return None
    return mapper((native_status or "").strip().lower(), (invoice_status or "").strip().lower())
