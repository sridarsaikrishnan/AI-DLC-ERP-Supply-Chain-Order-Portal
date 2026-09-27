"""Reseller GraphQL types — reseller-safe ONLY (no ERP identity, FR-19 by construction)."""

from __future__ import annotations

import strawberry


@strawberry.type
class OrderLineType:
    product_key: str
    quantity: float
    unit_of_measure: str


@strawberry.type
class TimelineEntryType:
    status: str
    occurred_at: str


@strawberry.type
class ResellerOrder:
    order_id: str
    client_reference: str
    status: str
    lines: list[OrderLineType]
    timeline: list[TimelineEntryType]


@strawberry.input
class OrderLineInput:
    product_key: str
    quantity: float
    unit_of_measure: str
