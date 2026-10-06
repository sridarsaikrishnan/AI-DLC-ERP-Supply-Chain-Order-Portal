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

# `CanonicalStatus` lives in `shared` now (ADR-0018) so `sales` can consume it without
# importing `integration`. Re-exported here so this module's own API is unchanged.
from src.shared.canonical_status import CanonicalStatus

__all__ = ["CanonicalStatus", "StatusMapper", "map_native_status", "STATUS_MAPPERS"]


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


def _map_netsuite(fields: dict[str, str]) -> CanonicalStatus | None:
    """Reads `fulfillmentstatus` — the human-reviewed field mapping for this ERP maps
    NetSuite's `fulfillmentstatus` -> canonical `fulfillment_status` (confidence 99%,
    see `docs/erps/netsuite.md`). Its three native values below are NetSuite's own
    standard sales order fulfillment picklist, all mapping to CONFIRMED for the same
    reason Odoo's "sale"/"done" both do: a fully-delivered order is a shipped *fact*
    tracked via Fulfillment records, not a lifecycle status this mapper advances
    (FR-A6) — so "fulfilled" doesn't get its own canonical status here.

    TODO(account-specific): the approved field mapping for this ERP connection has no
    field for CLOSED (billed/closed) or CANCELLED. NetSuite's own order lifecycle
    tracks those via a separate status/billing concept beyond `fulfillmentstatus` (e.g.
    a billing status, or a custom approval-workflow/order-status value) — which exact
    field and native value(s) this account uses for "cancelled"/"closed" isn't known
    without the live account (or that account's own saved-search/API setup). Add it
    here once confirmed; until then this mapper only ever returns CONFIRMED or None —
    never guess a value for the other two.
    """
    native = fields.get("fulfillmentstatus", "")
    if native in ("pending fulfillment", "partially fulfilled", "fulfilled"):
        return CanonicalStatus.CONFIRMED
    return None


# The one place a new ERP's status mapping is registered. Keyed by the same string an
# `ErpConnection.erp_type`/`ErpTarget.erp_type` carries (upper-cased).
STATUS_MAPPERS: dict[str, StatusMapper] = {
    "ODOO": _map_odoo,
    "NETSUITE": _map_netsuite,
}


def map_native_status(erp_type: str, fields: dict[str, str] | None) -> CanonicalStatus | None:
    mapper = STATUS_MAPPERS.get((erp_type or "").upper())
    if mapper is None:
        return None
    clean = {k: (v or "").strip().lower() for k, v in (fields or {}).items()}
    return mapper(clean)
