"""Snapshot value type (used to bound replay for long streams)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .events import utcnow


@dataclass(frozen=True)
class Snapshot:
    stream_id: str
    version: int
    state: dict[str, Any]
    taken_at: datetime = field(default_factory=utcnow)
