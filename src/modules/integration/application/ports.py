"""Ports for the integration module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.shared.types import ConnectionId, OrderId


class UnknownErpType(Exception):
    """No adapter is registered for this erp_type (see `infrastructure/registry.py`).
    A configuration gap, not a transient failure — callers should let this surface (e.g.
    to a DLQ for operator triage) rather than retry indefinitely without a code change."""


@dataclass(frozen=True)
class ErpTarget:
    """Resolved connection details handed to an adapter (secret already fetched)."""

    erp_type: str
    base_url: str
    database: str
    username: str
    secret: str


@dataclass(frozen=True)
class SubmissionResult:
    success: bool
    erp_order_id: str | None = None
    error: str | None = None
    terminal: bool = False  # True = permanent failure (do not retry)


class ErpAdapter(Protocol):
    def submit(self, target: ErpTarget, order_payload: dict[str, Any]) -> SubmissionResult: ...
    def fetch_status(self, target: ErpTarget, erp_order_id: str) -> str | None: ...
    def cancel(self, target: ErpTarget, erp_order_id: str) -> SubmissionResult: ...


class ConnectionResolver(Protocol):
    """Resolves a connection id to a ready-to-use target (base_url + resolved secret)."""

    def resolve(self, connection_id: ConnectionId) -> ErpTarget | None: ...


class OrderReader(Protocol):
    """Reads the ERP-neutral order payload needed to build the ERP request."""

    def read_payload(self, order_id: OrderId) -> dict[str, Any] | None: ...


class OrderCommandPort(Protocol):
    """Narrow command surface the delivery handler uses to drive the order aggregate."""

    def send_to_erp(self, order_id: OrderId, erp_order_id: str) -> None: ...
    def reject(self, order_id: OrderId, reason_code: str, message: str) -> None: ...
    def mark_retrying(self, order_id: OrderId, attempt: int, next_retry_at: str) -> None: ...
