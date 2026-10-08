"""Deterministic in-memory ERP adapter for tests and local runs (ERP_ADAPTER_MODE=stub)."""

from __future__ import annotations

from typing import Any

from src.shared.types import generate_id

from ..application.ports import ErpShipment, ErpTarget, SubmissionResult


class StubErpAdapter:
    """Accepts every submission and returns a generated erp order id."""

    capabilities = (
        frozenset()
    )  # deliberately none — this is a deterministic fake, not a real integration

    def __init__(self) -> None:
        self._status: dict[str, str] = {}

    def submit(self, target: ErpTarget, order_payload: dict[str, Any]) -> SubmissionResult:
        erp_order_id = generate_id("SO")
        self._status[erp_order_id] = "sale"
        return SubmissionResult(success=True, erp_order_id=erp_order_id)

    def fetch_status(self, target: ErpTarget, erp_order_id: str) -> dict[str, str] | None:
        status = self._status.get(erp_order_id)
        return {"state": status} if status is not None else None

    def fetch_shipments(self, target: ErpTarget, erp_order_id: str) -> list[ErpShipment]:
        return []

    def cancel(self, target: ErpTarget, erp_order_id: str) -> SubmissionResult:
        self._status[erp_order_id] = "cancel"
        return SubmissionResult(success=True, erp_order_id=erp_order_id)
