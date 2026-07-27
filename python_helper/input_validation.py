"""Strict scalar validation shared by deterministic input boundaries."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def strict_bool(value: Any, field: str) -> bool:
    """Accept only an actual JSON/YAML boolean, never truthy strings or numbers."""
    if type(value) is not bool:
        raise ValueError(f"{field} must be a boolean")
    return value


def strict_decimal(value: Any, field: str) -> Decimal:
    """Accept a finite numeric scalar while rejecting booleans and numeric strings."""
    if type(value) not in {int, float, Decimal}:
        raise ValueError(f"{field} must be a number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def strict_number(value: Any, field: str) -> float:
    """Return a finite float from an actual numeric scalar."""
    return float(strict_decimal(value, field))
