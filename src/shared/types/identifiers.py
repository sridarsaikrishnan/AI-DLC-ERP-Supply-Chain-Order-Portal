"""Distinct id types.

`NewType` gives mypy-level distinctness (you cannot pass a `ConnectionId` where a
`TenantId` is expected) with zero runtime cost. Ids are opaque, prefixed strings.
"""

from __future__ import annotations

from typing import NewType

TenantId = NewType("TenantId", str)
ConnectionId = NewType("ConnectionId", str)
ItemId = NewType("ItemId", str)
OrderId = NewType("OrderId", str)
BindingId = NewType("BindingId", str)
WebhookEndpointId = NewType("WebhookEndpointId", str)
