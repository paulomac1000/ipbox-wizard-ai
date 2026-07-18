"""Schema extension for historical-year and reconciliation-aware reports."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import output_schema as legacy

DECISION_JSON_SCHEMA: dict[str, Any] = deepcopy(legacy.DECISION_JSON_SCHEMA)
OUTPUT_JSON_SCHEMA: dict[str, Any] = deepcopy(legacy.OUTPUT_JSON_SCHEMA)

_stop_codes = DECISION_JSON_SCHEMA["schema"]["properties"]["stops"]["items"]["enum"]
for code in (
    "STOP_09",
    "STOP_10",
    "STOP_11",
    "STOP_12",
    "STOP_13",
    "STOP_14",
    "STOP_15",
    "STOP_16",
):
    if code not in _stop_codes:
        _stop_codes.append(code)

_result = OUTPUT_JSON_SCHEMA["schema"]["properties"]["result"]["properties"]
_mix_method = _result["klucz_MIX"]["properties"]["metoda"]["enum"]
if "przychodowa_w_dacie_kosztu" not in _mix_method:
    _mix_method.append("przychodowa_w_dacie_kosztu")

_tax = _result["podatek"]
for field in ("termomodernization_expired", "health_tax_credit_used"):
    if field not in _tax["required"]:
        _tax["required"].append(field)
    _tax["properties"][field] = deepcopy(legacy.NONNEGATIVE_MONEY)
