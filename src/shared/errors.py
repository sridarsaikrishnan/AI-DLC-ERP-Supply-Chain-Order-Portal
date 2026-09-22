"""Shared error types for the platform foundation."""


class PortalError(Exception):
    """Base error for all portal-domain errors."""


class ValidationError(PortalError):
    """Raised when canonical validation fails. Carries structured field errors."""

    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__(f"Validation failed with {len(errors)} error(s)")


class AuthorizationError(PortalError):
    """Raised when access is denied (e.g., missing tenant context - fail-closed)."""


class NotFoundError(PortalError):
    """Raised when a resource is not found (also used for cross-tenant access to avoid existence leaks)."""


class ConfigurationError(PortalError):
    """Raised for invalid/missing configuration (routing, mapping, instances)."""
