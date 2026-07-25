"""Annotate possible non-deductible expenses without deciding KUP from text alone.

Descriptions are weak signals. They may trigger a review candidate, but only an
explicit source flag or verified statutory classification may set ``KUP: false``.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .ipbox_calculator import has_non_deductible_description_signal


def is_known_non_deductible_description(description: str) -> bool:
    """Compatibility name for a token-aware candidate signal, not a KUP decision."""
    return has_non_deductible_description_signal(description)


def normalize_known_non_deductible_costs(scenario: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-copy a scenario and mark description-only review candidates.

    The historical name is retained for compatibility. The function never
    creates ``KUP: false`` and therefore cannot by itself alter tax or require a
    source-ledger correction.
    """
    normalized = deepcopy(dict(scenario))
    input_data = normalized.get("input")
    if not isinstance(input_data, dict):
        return normalized
    for month in input_data.get("miesiace", []) or []:
        if not isinstance(month, dict):
            continue
        for cost in month.get("koszty", []) or []:
            if not isinstance(cost, dict):
                continue
            if has_non_deductible_description_signal(str(cost.get("opis", ""))):
                cost["non_deductible_candidate"] = True
    return normalized
