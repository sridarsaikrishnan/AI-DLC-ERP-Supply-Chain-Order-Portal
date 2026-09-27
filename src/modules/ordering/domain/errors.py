"""Order domain errors."""

from __future__ import annotations


class OrderError(Exception):
    """Base class for order domain errors."""


class OrderInvalidTransition(OrderError):
    """Raised when a lifecycle transition is not allowed from the current state."""
