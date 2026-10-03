"""Fact event types this domain publishes (see `src/shared/messaging/facts.py`). Catalog
is plain CRUD (ADR-0002) — these are notifications, not a replayable log."""

from __future__ import annotations

ITEM_SYNCED = "ItemSynced"
