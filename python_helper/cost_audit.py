"""Deterministic cost-ledger audit and rounding policies.

This module keeps three concerns separate:

* whether an expense is tax-deductible at all,
* how a deductible MIX pool is split between IP and non-IP,
* whether any allocated amount is supported as a NEXUS component.

It never infers a taxpayer-specific interpretation identifier or evidence.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Any

from .input_validation import strict_bool, strict_decimal

MONEY = Decimal("0.01")
QUALIFIED_NEXUS_BASKETS = {"A", "B", "C", "D"}
ROUNDING_GRANULARITIES = {"per_cost_item", "monthly_pool"}


def money(value: Any) -> Decimal:
    return strict_decimal(value, "money value").quantize(MONEY, rounding=ROUND_HALF_UP)


def _fraction(value: Any, name: str) -> Decimal:
    result = strict_decimal(value, name)
    if not Decimal("0") <= result <= Decimal("1"):
        raise ValueError(f"{name} must be between 0 and 1")
    return result


def _cost_rows(input_data: Mapping[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for month in input_data.get("miesiace", []) or []:
        if not isinstance(month, Mapping):
            continue
        month_id = str(month.get("miesiac", ""))
        for cost in month.get("koszty", []) or []:
            if isinstance(cost, dict):
                rows.append((month_id, cost))
    return rows


def _first(mapping: Mapping[str, Any], *keys: str) -> Any | None:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _bool_flag(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().casefold()
    if normalized in {"tak", "yes", "true", "1", "kup"}:
        return True
    if normalized in {"nie", "no", "false", "0", "wykluczone", "non-kup", "not_kup"}:
        return False
    raise ValueError(f"unsupported boolean flag {value!r}")


def source_ledger_included_flag(cost: Mapping[str, Any]) -> bool | None:
    """Read an optional source-ledger flag using the strict scalar contract."""
    for field in (
        "source_ledger_included",
        "ujęty_w_kpir",
        "ujety_w_kpir",
    ):
        if field in cost:
            return strict_bool(cost[field], "cost.source_ledger_included")
    return None


def validate_cost_policy(input_data: Mapping[str, Any]) -> tuple[str, str | None]:
    policy = input_data.get("polityka_alokacji")
    mix = policy.get("koszty_MIX") if isinstance(policy, Mapping) else None
    if not isinstance(mix, Mapping):
        return "per_cost_item", None
    granularity = str(mix.get("rounding_granularity", "per_cost_item"))
    if granularity not in ROUNDING_GRANULARITIES:
        raise ValueError("koszty_MIX.rounding_granularity must be per_cost_item or monthly_pool")
    source = str(mix.get("źródło", ""))
    source_reference_raw = _first(mix, "źródło_ref", "source_reference", "sygnatura")
    source_reference = (
        str(source_reference_raw).strip() if source_reference_raw is not None else None
    )
    if source == "interpretacja_KIS" and not source_reference:
        raise ValueError(
            "koszty_MIX with źródło=interpretacja_KIS requires źródło_ref/source_reference"
        )
    if str(mix.get("metoda", "przychodowa_roczna")) == "przychodowa_roczna":
        for month_id, cost in _cost_rows(input_data):
            explicit = str(cost.get("koszyk", cost.get("kategoria", ""))).upper()
            if explicit in {"IP", "NON", "NIE", "WYKLUCZONE", "EXCLUDED"}:
                continue
            if (
                cost.get("allocation_key") is not None
                or str(cost.get("allocation_method", "")).strip()
            ):
                raise ValueError(
                    f"{month_id}: przychodowa_roczna forbids per-item allocation_key "
                    "and allocation_method for MIX costs; all MIX costs must be deferred "
                    "to annual true-up"
                )
    return granularity, source_reference


def _monthly_pool_allocations(amounts: list[Decimal], key: Decimal) -> list[Decimal]:
    if not amounts:
        return []
    if any(amount < 0 for amount in amounts):
        raise ValueError("cost amounts must be non-negative")
    total = sum(amounts, Decimal("0"))
    target_cents = int((money(total * key) * 100).to_integral_exact())
    raw_cents = [amount * key * 100 for amount in amounts]
    floor_cents = [int(value.to_integral_value(rounding=ROUND_DOWN)) for value in raw_cents]
    remaining = target_cents - sum(floor_cents)
    if not 0 <= remaining <= len(amounts):
        raise AssertionError("invalid largest-remainder cent count")
    order = sorted(
        range(len(amounts)),
        key=lambda index: (-(raw_cents[index] - floor_cents[index]), index),
    )
    for index in order[:remaining]:
        floor_cents[index] += 1
    allocations = [Decimal(cents) / 100 for cents in floor_cents]
    if sum(allocations, Decimal("0")) != money(total * key):
        raise AssertionError("monthly pool allocation did not preserve the rounded target")
    for allocation, amount in zip(allocations, amounts, strict=True):
        if allocation < 0 or allocation > amount:
            raise AssertionError("monthly pool allocation escaped item bounds")
    return allocations


def _recompute_nexus(reference: dict[str, Any]) -> None:
    totals = {name: Decimal("0") for name in ("A", "B", "C", "D", "poza_nexus")}
    for classification in reference.get("classifications", []):
        amount = money(classification.get("amount", 0))
        basket = str(classification.get("nexus_basket", "poza_nexus"))
        if basket in QUALIFIED_NEXUS_BASKETS:
            qualified = money(classification.get("nexus_amount", 0))
            if qualified > amount:
                raise ValueError("nexus_amount cannot exceed cost amount")
            totals[basket] += qualified
            totals["poza_nexus"] += amount - qualified
        else:
            totals["poza_nexus"] += amount
    denominator = totals["A"] + totals["B"] + totals["C"] + totals["D"]
    nexus = (
        Decimal("0")
        if denominator == 0
        else min(
            Decimal("1"),
            ((totals["A"] + totals["B"]) * Decimal("1.3")) / denominator,
        )
    )
    reference["result"]["nexus_koszty"] = {
        key: float(money(value)) for key, value in totals.items()
    }
    reference["result"]["nexus"] = round(float(nexus), 6)


def _source_ledger_audit(
    input_data: Mapping[str, Any],
    rows: list[tuple[str, dict[str, Any]]],
    classifications: list[dict[str, Any]],
) -> dict[str, Any]:
    source_classifications = classifications[: len(rows)]
    raw_costs = sum(
        (money(classification.get("amount", 0)) for classification in source_classifications),
        Decimal("0"),
    )
    deductible_costs = sum(
        (
            money(classification.get("ip_amount", 0))
            + money(classification.get("non_ip_amount", 0))
            for classification in source_classifications
        ),
        Decimal("0"),
    )
    excluded_total = sum(
        (
            money(classification.get("amount", 0))
            for classification in source_classifications
            if classification.get("basket") == "WYKLUCZONE"
        ),
        Decimal("0"),
    )

    explicitly_included = Decimal("0")
    explicit_status_seen = False
    for (_, cost), classification in zip(rows, source_classifications, strict=False):
        flag = source_ledger_included_flag(cost)
        if flag is not None:
            explicit_status_seen = True
        if flag is True and classification.get("basket") == "WYKLUCZONE":
            explicitly_included += money(classification.get("amount", 0))

    summary = input_data.get("podsumowanie_kpir")
    reported_raw = summary.get("koszty") if isinstance(summary, Mapping) else None
    reported = money(reported_raw) if reported_raw is not None else None
    inferred_included = Decimal("0")
    if reported is not None and excluded_total > 0 and abs(reported - raw_costs) <= MONEY:
        inferred_included = excluded_total
    excluded_recorded = max(explicitly_included, inferred_included)

    if excluded_recorded > 0:
        status = "REQUIRES_CORRECTION"
    elif reported is not None and abs(reported - deductible_costs) > MONEY:
        status = "MISMATCH"
    elif reported is not None or explicit_status_seen:
        status = "OK"
    else:
        status = "NOT_PROVIDED"

    correction_delta = (
        excluded_recorded
        if status == "REQUIRES_CORRECTION"
        else (
            abs(reported - deductible_costs)
            if status == "MISMATCH" and reported is not None
            else Decimal("0")
        )
    )
    return {
        "status": status,
        "reported_costs": float(reported) if reported is not None else None,
        "raw_input_costs": float(money(raw_costs)),
        "deductible_costs": float(money(deductible_costs)),
        "excluded_recorded_costs": float(money(excluded_recorded)),
        "correction_delta": float(money(correction_delta)),
    }


def apply_cost_audit(
    scenario: Mapping[str, Any], reference: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Apply explicit KUP, rounding, source-ledger and NEXUS evidence rules."""
    input_data = scenario.get("input")
    if not isinstance(input_data, Mapping):
        raise ValueError("scenario.input must be a mapping")
    granularity, source_reference = validate_cost_policy(input_data)
    rows = _cost_rows(input_data)
    classifications = reference.get("classifications")
    if not isinstance(classifications, list):
        raise ValueError("reference.classifications must be a list")

    warnings: set[str] = set()
    if classifications and len(classifications) < len(rows):
        raise ValueError("classification trace is shorter than source cost rows")

    for index, classification in enumerate(classifications):
        classification["allocation_period"] = None
        classification["rounding_granularity"] = "per_cost_item"
        classification["rounding_adjustment"] = 0.0
        classification["nexus_evidence"] = ""
        classification["nexus_basis"] = "explicit_amount"
        if index >= len(rows):
            continue
        month_id, cost = rows[index]
        classification["allocation_period"] = month_id
        classification["rounding_granularity"] = granularity

        kup_flag = _bool_flag(_first(cost, "KUP", "kup", "deductible"))
        if kup_flag is False:
            classification.update(
                {
                    "basket": "WYKLUCZONE",
                    "allocation_method": "excluded",
                    "allocation_key": None,
                    "ip_amount": 0.0,
                    "non_ip_amount": 0.0,
                    "nexus_source": "outside_nexus",
                    "nexus_basket": "poza_nexus",
                    "nexus_amount": 0.0,
                }
            )
            warnings.add("NON_DEDUCTIBLE_COST_EXCLUDED")

        if cost.get("non_deductible_candidate") is True and kup_flag is not False:
            warnings.add("NON_DEDUCTIBLE_CANDIDATE")

        evidence = str(
            _first(cost, "nexus_evidence", "br_evidence", "nexus_evidence_ref") or ""
        ).strip()
        classification["nexus_evidence"] = evidence
        basis = str(cost.get("nexus_basis", "explicit_amount"))
        if basis not in {"explicit_amount", "allocated_ip_cost"}:
            raise ValueError("nexus_basis must be explicit_amount or allocated_ip_cost")
        classification["nexus_basis"] = basis
        declared_nexus_source = str(cost.get("nexus_source", "outside_nexus"))
        declared_qualified = declared_nexus_source in {
            "own_br",
            "unrelated_br_contractor",
            "related_br_contractor",
            "acquired_ip",
        }
        if (
            classification.get("nexus_basket") in QUALIFIED_NEXUS_BASKETS or declared_qualified
        ) and not evidence:
            classification.update(
                {
                    "nexus_source": "outside_nexus",
                    "nexus_basket": "poza_nexus",
                    "nexus_amount": 0.0,
                    "nexus_basis": "explicit_amount",
                }
            )
            warnings.add("NEXUS_EVIDENCE_MISSING")

    if classifications and granularity == "monthly_pool":
        groups: dict[tuple[str, str, Decimal], list[int]] = defaultdict(list)
        for index, classification in enumerate(classifications[: len(rows)]):
            if classification.get("basket") != "MIX":
                continue
            key = classification.get("allocation_key")
            if key is None:
                raise ValueError("monthly_pool requires an allocation_key for every MIX item")
            group_key = (
                str(classification.get("allocation_period", "")),
                str(classification.get("allocation_method", "")),
                _fraction(key, "allocation_key"),
            )
            groups[group_key].append(index)
        for (_, _, key_raw), indices in groups.items():
            key = _fraction(key_raw, "allocation_key")
            amounts = [money(classifications[index].get("amount", 0)) for index in indices]
            allocated = _monthly_pool_allocations(amounts, key)
            for index, new_ip in zip(indices, allocated, strict=True):
                old_ip = money(classifications[index].get("ip_amount", 0))
                amount = money(classifications[index].get("amount", 0))
                classifications[index]["ip_amount"] = float(money(new_ip))
                classifications[index]["non_ip_amount"] = float(money(amount - new_ip))
                classifications[index]["rounding_adjustment"] = float(money(new_ip - old_ip))

    for classification in classifications[: len(rows)]:
        if (
            classification.get("nexus_basket") in QUALIFIED_NEXUS_BASKETS
            and classification.get("nexus_basis") == "allocated_ip_cost"
        ):
            classification["nexus_amount"] = float(money(classification.get("ip_amount", 0)))

    if classifications:
        annual_ip_cost = sum(
            (money(item.get("ip_amount", 0)) for item in classifications), Decimal("0")
        )
        annual_non_cost = sum(
            (money(item.get("non_ip_amount", 0)) for item in classifications), Decimal("0")
        )
        mix_total = sum(
            (
                money(item.get("amount", 0))
                for item in classifications
                if item.get("basket") == "MIX"
            ),
            Decimal("0"),
        )
        excluded_total = sum(
            (
                money(item.get("amount", 0))
                for item in classifications
                if item.get("basket") == "WYKLUCZONE"
            ),
            Decimal("0"),
        )
        reference["result"]["koszty_roczne"].update(
            {
                "IP": float(money(annual_ip_cost)),
                "NIE": float(money(annual_non_cost)),
                "MIX": float(money(mix_total)),
                "WYKLUCZONE": float(money(excluded_total)),
            }
        )
        ip_revenue = money(reference["result"]["przychody_roczne"]["IP"])
        non_revenue = money(reference["result"]["przychody_roczne"]["NIE"])
        reference["result"]["dochód_IP"] = float(money(ip_revenue - annual_ip_cost))
        reference["result"]["dochód_NIE"] = float(money(non_revenue - annual_non_cost))
        _recompute_nexus(reference)

    mix_result = reference["result"].get("klucz_MIX")
    if isinstance(mix_result, dict):
        mix_result["źródło_ref"] = source_reference
        mix_result["rounding_granularity"] = granularity

    source_audit = _source_ledger_audit(input_data, rows, classifications)
    if source_audit["status"] == "REQUIRES_CORRECTION":
        warnings.add("SOURCE_KPIR_REQUIRES_CORRECTION")
    elif source_audit["status"] == "MISMATCH":
        warnings.add("SOURCE_KPIR_TOTAL_MISMATCH")
    return source_audit, sorted(warnings)
