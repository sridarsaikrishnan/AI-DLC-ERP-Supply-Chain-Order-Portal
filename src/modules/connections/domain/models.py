"""Connection domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.shared.types import ConnectionId


class ErpType(str, Enum):
    ODOO = "ODOO"
    ERP_NEXT = "ERP_NEXT"


class ConnectionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


@dataclass
class ErpConnection:
    """One ERP instance (one Odoo db / one ERPNext site). Operator-only identity.

    `secret_ref` is a Secrets Manager reference — never the raw credential (SECURITY-12).
    `instance_label` is operator-only and must never reach a reseller surface (FR-19).

    `webhook_secret_ref` is a SEPARATE Secrets Manager reference from `secret_ref`: the
    former is our credential for logging into the ERP, the latter is the credential the
    ERP uses to prove a webhook call came from it. Reusing one secret for both would mean
    a leaked webhook URL (which, for Odoo's shared-secret-in-path scheme, is the ERP admin
    UI's Automation Rule config — not a secret store) also leaks ERP login access. `None`
    until a connection's webhook is onboarded (target-architecture.md 5a: until then it
    silently relies on the reconciliation sweeper).
    """

    connection_id: ConnectionId
    erp_type: ErpType
    instance_label: str
    base_url: str
    database: str
    username: str
    secret_ref: str
    status: ConnectionStatus = ConnectionStatus.ACTIVE
    webhook_secret_ref: str | None = None

    @property
    def is_active(self) -> bool:
        return self.status is ConnectionStatus.ACTIVE
