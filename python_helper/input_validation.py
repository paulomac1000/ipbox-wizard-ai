"""Strict scalar validation shared by deterministic input boundaries."""

from __future__ import annotations

from typing import Any


def strict_bool(value: Any, field: str) -> bool:
    """Accept only an actual JSON/YAML boolean, never truthy strings or numbers."""
    if type(value) is not bool:
        raise ValueError(f"{field} must be a boolean")
    return value
