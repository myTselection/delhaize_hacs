"""Small helpers for Delhaize API response dictionaries."""

from __future__ import annotations

from typing import Any


def nested_get(data: dict[str, Any], *path: str, default: Any = None) -> Any:
    """Return a nested value from a Delhaize response dictionary."""
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value
