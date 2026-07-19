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
    "SOURCE_KPIR_REQUIRES_CORRECTION",
):
    if code not in _stop_codes:
        _stop_codes.append(code)

_review_codes = DECISION_JSON_SCHEMA["schema"]["properties"]["reviews"]["items"]["enum"]
if "REVIEW_18" not in _review_codes:
    _review_codes.append("REVIEW_18")

# The assembled report must enforce the same channel-specific code sets as the
# small decision envelope. A generic CODE pattern here would let a tampered
# report route REVIEW codes through stops even though live parsing rejects it.
_decision_properties = DECISION_JSON_SCHEMA["schema"]["properties"]
_report_root = OUTPUT_JSON_SCHEMA["schema"]
_report_channels = _report_root["properties"]["stops_reviews"]["properties"]
_report_channels["stops"]["items"] = deepcopy(_decision_properties["stops"]["items"])
_report_channels["reviews"]["items"] = deepcopy(_decision_properties["reviews"]["items"])

_result = _report_root["properties"]["result"]["properties"]
_mix = _result["klucz_MIX"]
_mix_method = _mix["properties"]["metoda"]["enum"]
if "przychodowa_w_dacie_kosztu" not in _mix_method:
    _mix_method.append("przychodowa_w_dacie_kosztu")
for field in ("źródło_ref", "rounding_granularity"):
    if field not in _mix["required"]:
        _mix["required"].append(field)
_mix["properties"]["źródło_ref"] = {"anyOf": [{"type": "null"}, {"type": "string", "minLength": 1}]}
_mix["properties"]["rounding_granularity"] = {"enum": ["per_cost_item", "monthly_pool"]}

_tax = _result["podatek"]
for field in (
    "thermomodernization_used",
    "termomodernization_expired",
    "health_tax_credit_used",
    "podstawa_zwykła",
    "dochód_IP_po_uldze_BR",
    "dochód_IP_kwalifikowany",
    "dochód_IP_poza_preferencją",
):
    if field not in _tax["required"]:
        _tax["required"].append(field)
    _tax["properties"][field] = deepcopy(legacy.NONNEGATIVE_MONEY)

_classification = _report_root["properties"]["classifications"]["items"]
for field in (
    "allocation_period",
    "rounding_granularity",
    "rounding_adjustment",
    "nexus_evidence",
    "nexus_basis",
):
    if field not in _classification["required"]:
        _classification["required"].append(field)
_classification["properties"]["allocation_period"] = {
    "anyOf": [
        {"type": "null"},
        {"type": "string", "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"},
    ]
}
_classification["properties"]["rounding_granularity"] = {"enum": ["per_cost_item", "monthly_pool"]}
_classification["properties"]["rounding_adjustment"] = deepcopy(legacy.MONEY)
_classification["properties"]["nexus_evidence"] = {"type": "string"}
_classification["properties"]["nexus_basis"] = {"enum": ["explicit_amount", "allocated_ip_cost"]}

for field in ("source_ledger_audit", "correction_preview"):
    if field not in _report_root["required"]:
        _report_root["required"].append(field)

_nullable_nonnegative_money = {"anyOf": [{"type": "null"}, deepcopy(legacy.NONNEGATIVE_MONEY)]}
_nullable_money = {"anyOf": [{"type": "null"}, deepcopy(legacy.MONEY)]}
_report_root["properties"]["source_ledger_audit"] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "status",
        "reported_costs",
        "raw_input_costs",
        "deductible_costs",
        "excluded_recorded_costs",
        "correction_delta",
    ],
    "properties": {
        "status": {"enum": ["NOT_PROVIDED", "OK", "REQUIRES_CORRECTION", "MISMATCH"]},
        "reported_costs": deepcopy(_nullable_nonnegative_money),
        "raw_input_costs": deepcopy(legacy.NONNEGATIVE_MONEY),
        "deductible_costs": deepcopy(legacy.NONNEGATIVE_MONEY),
        "excluded_recorded_costs": deepcopy(legacy.NONNEGATIVE_MONEY),
        "correction_delta": deepcopy(legacy.NONNEGATIVE_MONEY),
    },
}
_report_root["properties"]["correction_preview"] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "status",
        "source_kpir_correction_required",
        "return_correction_required",
        "relief_adjustment_required",
        "tax_unchanged_only_if_reliefs_updated",
        "corrected_total_tax",
        "corrected_overpayment",
        "thermomodernization_used",
        "thermomodernization_carry_over",
    ],
    "properties": {
        "status": {"enum": ["NOT_NEEDED", "AVAILABLE", "UNAVAILABLE"]},
        "source_kpir_correction_required": {"type": "boolean"},
        "return_correction_required": {"type": "boolean"},
        "relief_adjustment_required": {"type": "boolean"},
        "tax_unchanged_only_if_reliefs_updated": {"type": "boolean"},
        "corrected_total_tax": deepcopy(_nullable_nonnegative_money),
        "corrected_overpayment": deepcopy(_nullable_money),
        "thermomodernization_used": deepcopy(_nullable_nonnegative_money),
        "thermomodernization_carry_over": deepcopy(_nullable_nonnegative_money),
    },
}
