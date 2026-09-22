"""Correlation-id handling and propagation (NFR P-5).

Inbound X-Correlation-Id is accepted if present, otherwise a new id is generated
at API ingress. The current correlation id is stored in a context variable so it
can be read by the logger and copied onto enqueued jobs.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

CORRELATION_HEADER = "X-Correlation-Id"


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def set_correlation_id(value: str | None) -> str:
    cid = value or new_correlation_id()
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str | None:
    return _correlation_id.get()
