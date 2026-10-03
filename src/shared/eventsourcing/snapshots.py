"""Snapshot value type (used to bound replay for long streams)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .events import utcnow

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class Snapshot:
    stream_id: str
    version: int
    state: dict[str, Any]
    taken_at: datetime = field(default_factory=utcnow)
