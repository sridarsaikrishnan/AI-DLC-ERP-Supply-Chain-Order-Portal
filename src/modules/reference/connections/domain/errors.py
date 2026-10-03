"""Connection domain errors."""

from __future__ import annotations


class ConnectionNotFound(Exception):
    """Raised when a referenced connection does not exist."""
