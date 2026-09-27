"""Tenancy domain errors."""

from __future__ import annotations


class TenancyError(Exception):
    """Base class for tenancy errors."""


class BindingConflict(TenancyError):
    """Raised when a binding would violate a uniqueness rule."""


class BindingNotFound(TenancyError):
    """Raised when a referenced binding does not exist."""
