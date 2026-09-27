"""Order value objects and lifecycle states."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class OrderLine:
    product_key: str
    quantity: float
    unit_of_measure: str


class OrderState(str, Enum):
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY"
    SENT_TO_ERP = "SENT_TO_ERP"
    CONFIRMED = "CONFIRMED"
    FULFILLED = "FULFILLED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


# States from which no further reseller-visible transition happens.
TERMINAL_STATES = frozenset({OrderState.CLOSED, OrderState.CANCELLED, OrderState.REJECTED})
