"""Compatibility module for Delhaize API helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

_T = TypeVar("_T")


def passthrough(func: Callable[..., Awaitable[_T]]) -> Callable[..., Awaitable[_T]]:
    """Return an async function unchanged while preserving metadata."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> _T:
        return await func(*args, **kwargs)

    return wrapper
