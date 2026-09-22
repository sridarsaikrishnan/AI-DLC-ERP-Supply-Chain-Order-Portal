"""ErpAdapter interface, AdapterResult, and AdapterRegistry (LC-U3-1, P-U3-1)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from ..foundation.config.models import ErpType


class AdapterAction(str, Enum):
    CANCEL = "CANCEL"
    AMEND = "AMEND"
    RESUBMIT = "RESUBMIT"


@dataclass
class AdapterResult:
    success: bool
    erp_reference: str | None = None
    native_status: str | None = None
    error: str | None = None
    terminal: bool = False  # True = permanent failure (do not retry)


class ErpAdapter(Protocol):
    def submit(self, erp_payload: dict, connection: str) -> AdapterResult: ...
    def fetch_status(self, erp_reference: str, connection: str) -> AdapterResult: ...
    def send_corrective_action(self, action: AdapterAction, erp_reference: str, connection: str, payload: dict | None = None) -> AdapterResult: ...
    def check_connectivity(self, connection: str) -> bool: ...


class AdapterRegistry:
    """Maps ErpType -> adapter instance. Adding a new ERP = register a new adapter."""

    def __init__(self) -> None:
        self._adapters: dict[ErpType, ErpAdapter] = {}

    def register(self, erp_type: ErpType, adapter: ErpAdapter) -> None:
        self._adapters[erp_type] = adapter

    def get(self, erp_type: ErpType) -> ErpAdapter | None:
        return self._adapters.get(erp_type)
