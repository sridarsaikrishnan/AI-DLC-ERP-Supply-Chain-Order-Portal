"""Pure native-ERP-status -> canonical-status mapping (a PBT target).

Total function: returns a `CanonicalStatus` for recognized inputs and `None` (no
transition) for anything unrecognized — never raises.
"""

from __future__ import annotations

from enum import Enum


class CanonicalStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    FULFILLED = "FULFILLED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


def map_native_status(
    erp_type: str, native_status: str | None, invoice_status: str | None = None
) -> CanonicalStatus | None:
    erp = (erp_type or "").upper()
    native = (native_status or "").strip().lower()
    invoice = (invoice_status or "").strip().lower()

    if erp == "ODOO":
        if native == "cancel":
            return CanonicalStatus.CANCELLED
        if invoice == "invoiced":
            return CanonicalStatus.CLOSED
        if native == "done":
            return CanonicalStatus.FULFILLED
        if native == "sale":
            return CanonicalStatus.CONFIRMED
        return None

    if erp == "ERP_NEXT":
        return {
            "to deliver and bill": CanonicalStatus.CONFIRMED,
            "to bill": CanonicalStatus.CONFIRMED,
            "to deliver": CanonicalStatus.CONFIRMED,
            "completed": CanonicalStatus.FULFILLED,
            "closed": CanonicalStatus.CLOSED,
            "cancelled": CanonicalStatus.CANCELLED,
        }.get(native)

    return None
