"""MappingEngine (LC-U3-3, BR-U3-4, Q1=A).

Applies MappingDefinition to translate canonical <-> ERP payloads.
Field entries copy source_path -> target_path with optional value_map.
Expressions are treated as direct/renamed copies for MVP (no transform engine).
Pure functions — partial PBT round-trip candidate.
"""

from __future__ import annotations

from ..foundation.config.models import MappingDefinition


def _get_path(obj: dict, path: str):
    current = obj
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _set_path(obj: dict, path: str, value) -> None:
    parts = path.split(".")
    current = obj
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def apply_mapping(source: dict, mapping: MappingDefinition) -> dict:
    """Produce the target payload from `source` using the mapping definition."""
    target: dict = {}
    for entry in mapping.field_entries:
        value = _get_path(source, entry.source_path)
        if value is not None and entry.value_map:
            # translate discrete values; unknown values pass through (flagged elsewhere)
            value = entry.value_map.get(str(value), value)
        if value is not None:
            _set_path(target, entry.target_path, value)
    # expressions treated as direct copies: expression string is a source path (MVP)
    for expr in mapping.expressions:
        value = _get_path(source, expr.expression)
        if value is not None:
            _set_path(target, expr.target_path, value)
    return target


def to_erp(canonical: dict, mapping: MappingDefinition) -> dict:
    return apply_mapping(canonical, mapping)


def from_erp(native: dict, mapping: MappingDefinition) -> dict:
    return apply_mapping(native, mapping)
