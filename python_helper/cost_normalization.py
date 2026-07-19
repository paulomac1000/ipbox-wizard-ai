"""Normalize generic non-deductible expense signals before tax allocation.

This module contains no taxpayer-specific data. It reuses the same generic
private and statutory exclusion signals as the deterministic cost classifier so
an explicit IP/NON/MIX label cannot override a known non-deductible character.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .ipbox_calculator import EXCLUDED_PATTERNS, PRIVATE_KEYWORDS


def is_known_non_deductible_description(description: str) -> bool:
    """Return whether a description matches a generic private/statutory exclusion."""
    normalized = description.casefold()
    return any(keyword in normalized for keyword in PRIVATE_KEYWORDS) or any(
        re.search(pattern, normalized) for pattern in EXCLUDED_PATTERNS
    )


def normalize_known_non_deductible_costs(scenario: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-copy a scenario and mark known non-deductible costs as ``KUP: false``.

    The normalization is deliberately applied before the legacy allocation
    oracle runs. It prevents an explicit tax basket from allowing a known
    private expense to reduce either ordinary or preferential income.
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
            if is_known_non_deductible_description(str(cost.get("opis", ""))):
                cost["KUP"] = False
    return normalized
