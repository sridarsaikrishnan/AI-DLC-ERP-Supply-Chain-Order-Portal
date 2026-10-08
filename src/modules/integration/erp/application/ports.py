"""Ports for the integration module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from src.shared.types import ConnectionId, OrderId


class UnknownErpType(Exception):
    """No adapter is registered for this erp_type (see `infrastructure/registry.py`).
    A configuration gap, not a transient failure — callers should let this surface (e.g.
    to a DLQ for operator triage) rather than retry indefinitely without a code change."""


@dataclass(frozen=True)
class ErpTarget:
    """Resolved connection details handed to an adapter (secret already fetched).

    `credentials` is a generic, per-adapter-interpreted bag of non-secret connection
    parameters (Odoo: `{"database", "username"}`; a token-auth ERP might need an account
    id, or nothing here at all). `secret` stays its own field, resolved via Secrets
    Manager — never put in `credentials`."""

    erp_type: str
    base_url: str
    credentials: dict[str, str]
    secret: str


@dataclass(frozen=True)
class ErpShipmentLine:
    product_key: str
    quantity: str  # decimal as text, same shape the shipment event already carries


@dataclass(frozen=True)
class ErpShipment:
    """One done delivery in the ERP. `erp_shipment_id` is the ERP's own id, stable across polls."""

    erp_shipment_id: str
    lines: tuple[ErpShipmentLine, ...]
    carrier: str | None = None
    tracking_number: str | None = None
    proof_of_delivery: str | None = None


@dataclass(frozen=True)
class ErpInvoice:
    """One posted customer invoice in the ERP. `erp_invoice_id` is stable across polls."""

    erp_invoice_id: str
    lines: tuple[ErpShipmentLine, ...]
    number: str | None = None


@dataclass(frozen=True)
class ErpPartnerOrderLine:
    product_key: str
    quantity: str
    unit_price: str = ""
    currency: str = "USD"


@dataclass(frozen=True)
class ErpPartnerOrder:
    """A sales order that already exists in the ERP. `erp_order_id` is its document name."""

    erp_order_id: str
    client_reference: str
    lines: tuple[ErpPartnerOrderLine, ...]


@dataclass(frozen=True)
class SubmissionResult:
    success: bool
    erp_order_id: str | None = None
    error: str | None = None
    terminal: bool = False  # True = permanent failure (do not retry)


# The vocabulary a capability can name — not enforced (no gating logic reads this yet,
# ADR-0015), just a declared, inspectable contract instead of implicit per-adapter code.
KNOWN_CAPABILITIES = frozenset(
    {"tax", "uom", "idempotency", "fail_closed_product", "multi_currency", "partial_fulfillment"}
)


class ErpAdapter(Protocol):
    # Declared, not yet consumed for behavioral gating (ADR-0015) — `DeliveryHandler`
    # logs it so a capability gap is visible, but still calls `submit` the same way for
    # every adapter; real gating is deferred until a second adapter actually needs to
    # differ, so the axes aren't guessed from a sample size of one.
    capabilities: frozenset[str]

    def submit(self, target: ErpTarget, order_payload: dict[str, Any]) -> SubmissionResult: ...
    def fetch_status(self, target: ErpTarget, erp_order_id: str) -> dict[str, str] | None: ...
    def fetch_partner_orders(self, target: ErpTarget, partner_id: str) -> list[ErpPartnerOrder]: ...
    def fetch_shipments(self, target: ErpTarget, erp_order_id: str) -> list[ErpShipment]: ...
    def fetch_invoices(self, target: ErpTarget, erp_order_id: str) -> list[ErpInvoice]: ...
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
