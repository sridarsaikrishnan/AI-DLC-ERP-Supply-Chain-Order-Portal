"""ERP Next stub adapter (LC-U3-2, Q2=B).

Simulates ERP Next behavior so the PoC runs end-to-end without a live instance.
Deterministic status progression; cancel rejected once 'Shipped'.
"""

from __future__ import annotations

import uuid

from ..adapter import AdapterAction, AdapterResult

# In-memory simulated ERP state keyed by erp_reference.
_STATE: dict[str, str] = {}

# Deterministic progression used by fetch_status.
_PROGRESSION = ["Accepted", "Processing", "Shipped", "Invoiced"]


class ErpNextStubAdapter:
    erp_type_name = "ERP_NEXT"

    def submit(self, erp_payload: dict, connection: str) -> AdapterResult:
        ref = f"ERPNEXT-{uuid.uuid4().hex[:8]}"
        _STATE[ref] = "Accepted"
        return AdapterResult(success=True, erp_reference=ref, native_status="Accepted")

    def fetch_status(self, erp_reference: str, connection: str) -> AdapterResult:
        current = _STATE.get(erp_reference)
        if current is None:
            return AdapterResult(success=False, error="unknown reference", terminal=True)
        # advance one step per poll, capped at Invoiced
        if current in _PROGRESSION:
            idx = _PROGRESSION.index(current)
            if idx < len(_PROGRESSION) - 1:
                current = _PROGRESSION[idx + 1]
                _STATE[erp_reference] = current
        return AdapterResult(success=True, erp_reference=erp_reference, native_status=current)

    def send_corrective_action(self, action: AdapterAction, erp_reference: str, connection: str, payload: dict | None = None) -> AdapterResult:
        current = _STATE.get(erp_reference)
        if current is None:
            return AdapterResult(success=False, error="unknown reference", terminal=True)
        if action == AdapterAction.CANCEL:
            if current in ("Shipped", "Invoiced"):
                return AdapterResult(success=False, error="cannot cancel: already shipped", terminal=True)
            _STATE[erp_reference] = "Cancelled"
            return AdapterResult(success=True, erp_reference=erp_reference, native_status="Cancelled")
        if action == AdapterAction.AMEND:
            if current in ("Shipped", "Invoiced", "Cancelled"):
                return AdapterResult(success=False, error="cannot amend in current state", terminal=True)
            return AdapterResult(success=True, erp_reference=erp_reference, native_status=current)
        if action == AdapterAction.RESUBMIT:
            return self.submit(payload or {}, connection)
        return AdapterResult(success=False, error="unknown action", terminal=True)

    def check_connectivity(self, connection: str) -> bool:
        return True
