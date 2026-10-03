"""Tenancy domain model: the tenant↔connection binding."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.types import BindingId, ConnectionId, TenantId


class BindingStatus(str, Enum):
    TO_VERIFY = "TO_VERIFY"
    VERIFIED = "VERIFIED"
    REMOVED = "REMOVED"


@dataclass
class TenantConnectionBinding:
    """Maps a reseller to their customer record inside one ERP connection.

    `erp_customer_id` is operator-only (never exposed to resellers, FR-19).
    """

    binding_id: BindingId
    tenant_id: TenantId
    connection_id: ConnectionId
    erp_customer_id: str
    status: BindingStatus = BindingStatus.TO_VERIFY

    @property
    def is_verified(self) -> bool:
        return self.status is BindingStatus.VERIFIED
