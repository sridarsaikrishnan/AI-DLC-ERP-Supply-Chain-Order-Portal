"""Fact event types this domain publishes (see `src/shared/messaging/facts.py`).
`tenancy` is plain CRUD (ADR-0002) — these are notifications, not a replayable log."""

from __future__ import annotations

BINDING_CREATED = "BindingCreated"
BINDING_VERIFIED = "BindingVerified"
BINDING_REMOVED = "BindingRemoved"
