from __future__ import annotations

import pytest

from src.shared.config.settings import _ALL_WORKER_ROLES, _parse_worker_roles


def test_all_resolves_to_every_role() -> None:
    assert _parse_worker_roles("all") == _ALL_WORKER_ROLES
    assert _parse_worker_roles("ALL") == _ALL_WORKER_ROLES  # case-insensitive


def test_single_role() -> None:
    assert _parse_worker_roles("reconcile") == {"reconcile"}


def test_comma_separated_roles_combine_into_one_process() -> None:
    assert _parse_worker_roles("relay, reconcile") == {"relay", "reconcile"}


def test_unknown_role_raises_rather_than_silently_running_nothing() -> None:
    with pytest.raises(ValueError, match="unknown WORKER_ROLE"):
        _parse_worker_roles("made-up-role")
