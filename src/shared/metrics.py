"""Minimal in-process metrics (NFR-U0-OBS-3).

A lightweight counter registry sufficient for the PoC; exposes a text snapshot
for the /metrics endpoint. Swap for Prometheus client later.
"""

from __future__ import annotations

import threading
from collections import defaultdict

_lock = threading.Lock()
_counters: dict[str, float] = defaultdict(float)


def increment(name: str, value: float = 1.0) -> None:
    with _lock:
        _counters[name] += value


def snapshot() -> dict[str, float]:
    with _lock:
        return dict(_counters)


def render_text() -> str:
    lines = [f"{name} {value}" for name, value in sorted(snapshot().items())]
    return "\n".join(lines) + "\n"
