"""Async job model (LC-2, BR-3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum


class JobType(str, Enum):
    SUBMISSION = "SUBMISSION"
    CORRECTIVE_ACTION = "CORRECTIVE_ACTION"
    STATUS_SYNC = "STATUS_SYNC"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass
class Job:
    type: JobType
    payload: dict
    tenant_id: str
    dedupe_key: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    max_attempts: int = 5
    correlation_id: str | None = None
