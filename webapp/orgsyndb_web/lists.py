"""Shared query-choice validation and sorting helpers for list views."""

from collections.abc import Callable, Container, Sequence
from typing import Any, TypeVar

T = TypeVar("T")


def clean_choice(value: str, allowed: Container[str],
                 default: str = "") -> str:
    """Return VALUE when it belongs to ALLOWED, otherwise DEFAULT."""
    return value if value in allowed else default


def sort_rows(rows: Sequence[T], value: Callable[[T], Any],
              descending: bool = False) -> list[T]:
    """Return ROWS ordered by VALUE, reversed when DESCENDING, placing
    rows whose VALUE is None last in their original order; ties keep
    their order."""
    present = [row for row in rows if value(row) is not None]
    present.sort(key=value, reverse=descending)
    return present + [row for row in rows if value(row) is None]
