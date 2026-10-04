"""Order domain errors."""

from __future__ import annotations


class OrderError(Exception):
    """Base class for order domain errors."""


class OrderInvalidTransition(OrderError):
    """Raised when a lifecycle transition is not allowed from the current state."""


class DuplicateOrderReference(OrderError):
    """This reseller already has an order with this `client_reference` (their own PO
    number). Checked against the projection (read model), so there's a narrow race
    window: two near-simultaneous submissions with the same number can both pass this
    check before either one's projection exists. The database's own UNIQUE constraint
    (migration 0009) is the backstop for that case — see
    `PostgresOrderProjectionStore.create`."""

    def __init__(self, client_reference: str) -> None:
        super().__init__(f"an order with reference '{client_reference}' already exists")
        self.client_reference = client_reference
