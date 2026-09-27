"""Prefixed id generation.

Prefixes make ids self-describing in logs and payloads (`conn_…`, `tnt_…`). Uses uuid4
here for zero dependencies and local runnability; production may swap to ULID/UUIDv7
(time-sortable) behind this one function without changing call sites.
"""

from __future__ import annotations

import uuid


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
