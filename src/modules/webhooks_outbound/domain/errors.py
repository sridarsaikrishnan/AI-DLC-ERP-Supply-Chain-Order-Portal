"""Outbound webhook domain errors."""

from __future__ import annotations


class WebhookEndpointNotFound(Exception):
    """Raised when a referenced webhook endpoint does not exist."""
