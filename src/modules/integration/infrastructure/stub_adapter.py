"""Deterministic in-memory ERP adapter for tests and local runs (ERP_ODOO_MODE=stub)."""

from __future__ import annotations

from typing import Any

from src.shared.types import generate_id

from ..application.ports import ErpTarget, SubmissionResult


class StubErpAdapter:
    """Accepts every submission and returns a generated erp order id."""

    def __init__(self) -> None:
        self._status: dict[str, str] = {}

    def submit(self, target: ErpTarget, order_payload: dict[str, Any]) -> SubmissionResult:
        erp_order_id = generate_id("SO")
        self._status[erp_order_id] = "sale"
        return SubmissionResult(success=True, erp_order_id=erp_order_id)

    def fetch_status(self, target: ErpTarget, erp_order_id: str) -> str | None:
        return self._status.get(erp_order_id)

    def cancel(self, target: ErpTarget, erp_order_id: str) -> SubmissionResult:
        self._status[erp_order_id] = "cancel"
        return SubmissionResult(success=True, erp_order_id=erp_order_id)
