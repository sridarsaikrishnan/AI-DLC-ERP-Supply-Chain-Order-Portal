from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from src.modules.integration.application.reconcile import ReconcileSweeper
from src.worker.scheduler import ReconcileScheduler


class _FakeLock:
    """Records every acquire attempt; a connection_id in `held_by_other` simulates
    another worker replica already holding that connection's lock."""

    def __init__(self, held_by_other: set[str] | None = None) -> None:
        self.attempts: list[str] = []
        self._held_by_other = held_by_other or set()

    @contextmanager
    def try_acquire(self, connection_id: str) -> Iterator[bool]:
        self.attempts.append(connection_id)
        yield connection_id not in self._held_by_other


class _FakeSweeper:
    def __init__(self) -> None:
        self.ran_for: list[str] = []

    def run(self, connection_id: str, erp_order_ids: list[str]) -> int:
        self.ran_for.append(connection_id)
        return 0


def _scheduler(sweeper: _FakeSweeper, lock: _FakeLock | None) -> ReconcileScheduler:
    return ReconcileScheduler(
        sweeper,  # type: ignore[arg-type]
        connections_provider=lambda: ["conn_1", "conn_2"],  # type: ignore[list-item]
        open_orders_provider=lambda _c: [],
        interval_seconds=900,
        lock=lock,  # type: ignore[arg-type]
    )


def test_sweeps_every_connection_when_no_lock_configured() -> None:
    sweeper = _FakeSweeper()
    _scheduler(sweeper, lock=None).run_once()
    assert sweeper.ran_for == ["conn_1", "conn_2"]


def test_sweeps_only_connections_it_actually_acquires() -> None:
    sweeper = _FakeSweeper()
    lock = _FakeLock(held_by_other={"conn_1"})  # another replica is already sweeping conn_1
    _scheduler(sweeper, lock=lock).run_once()

    assert lock.attempts == ["conn_1", "conn_2"]  # tried both
    assert sweeper.ran_for == ["conn_2"]  # only swept the one it actually acquired


def test_one_connections_exception_does_not_stop_the_sweep_for_others() -> None:
    class _FailingSweeper:
        def __init__(self) -> None:
            self.ran_for: list[str] = []

        def run(self, connection_id: str, erp_order_ids: list[str]) -> int:
            if connection_id == "conn_1":
                raise RuntimeError("bad secret")
            self.ran_for.append(connection_id)
            return 0

    sweeper = _FailingSweeper()
    _scheduler(sweeper, lock=None).run_once()  # type: ignore[arg-type]
    assert sweeper.ran_for == ["conn_2"]
