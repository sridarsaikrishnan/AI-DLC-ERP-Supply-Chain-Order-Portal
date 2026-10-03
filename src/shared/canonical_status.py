"""Canonical order status — shared vocabulary.

The set of lifecycle statuses an ERP poll/webhook can drive an order toward. It lives in
`shared` (not in `integration`) because two groups speak it: `integration` maps a native
ERP status *into* it, and `sales` (the Order's `StatusApplier`) consumes it to advance the
lifecycle. Keeping it here lets `sales` stay independent of `integration` (ADR-0017/0018).

Increment 5 removed `FULFILLED` (FR-A6): "fully delivered" is a shipped/delivered fact
tracked via Shipment records, not a lifecycle status an ERP status string advances.
"""

from __future__ import annotations

from enum import Enum


class CanonicalStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
