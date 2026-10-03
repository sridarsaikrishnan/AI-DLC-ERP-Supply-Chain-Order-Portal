"""Pure reverse-attribution helpers (inbound ERP data -> the right tenant).

'Attribution before publication': inbound customer/item data is attributed to a tenant
only through a VERIFIED binding. Unattributable data returns None and must be dropped,
never broadcast.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.types import TenantId

    from .models import TenantConnectionBinding


def resolve_tenant_for_customer(binding: TenantConnectionBinding | None) -> TenantId | None:
    """Return the owning tenant only if a VERIFIED binding exists."""
    if binding is None or not binding.is_verified:
        return None
    return binding.tenant_id


def is_item_visible_to_tenant(has_verified_binding: bool) -> bool:
    """An item from a connection is visible to a reseller only if they are bound to it."""
    return has_verified_binding
