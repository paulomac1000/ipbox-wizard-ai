"""Year-aware and reconciliation-aware wrapper around the stable scenario oracle."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from python_helper import calculate_tax_for_year, strict_year
from python_helper.cost_audit import apply_cost_audit, validate_cost_policy
from python_helper.cost_normalization import normalize_known_non_deductible_costs
from python_helper.input_validation import strict_bool
from python_helper.ipbox_calculator import calculate_overpayment, money, tax_round

from . import oracle as legacy
from .allocation_guard_safe import audit_facts
from .oracle_adapter import (
    invoice_amount,
    legacy_safe_copy,
    month_invoices,
    number,
    prepare_scenario,
)
from .oracle_guards import (
    REVIEW_FACT_TO_CODE,
    STOP_FACT_TO_CODE,
    derive_decision_codes,
    year_facts,
    zero_after_stop,
)

ScenarioError = legacy.ScenarioError
CORRECTION_ONLY_STOPS = {"STOP_12", "SOURCE_KPIR_REQUIRES_CORRECTION"}

__all__ = [
    "REVIEW_FACT_TO_CODE",
    "STOP_FACT_TO_CODE",
    "ScenarioError",
    "compute_reference",
    "derive_decision_codes",
    "validate_scenario",
]


def _first(mapping: Mapping[str, Any], *keys: str) -> Any | None:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def validate_scenario(scenario: dict[str, Any]) -> None:
    transformed, _shares, _method = prepare_scenario(scenario)
    try:
        legacy.validate_scenario(legacy_safe_copy(transformed, for_validation=True))
        input_data = scenario.get("input")
        if not isinstance(input_data, Mapping):
            raise ScenarioError("input must be a mapping")
        validate_cost_policy(input_data)
    except legacy.ScenarioError:
        raise
    except ValueError as exc:
        raise ScenarioError(str(exc)) from exc
    year_facts(scenario)


def _tax_result(tax: Mapping[str, Any], signed_settlement: float) -> dict[str, Any]:
    return {
        "podstawa_IP": tax["ip_base_rounded"],
        # Compatibility name: this is now the entire ordinary-rate base and may
        # include the part of IP income not covered by NEXUS.
        "podstawa_NIE": tax["non_ip_base_rounded"],
        "podstawa_zwykła": tax["ordinary_base_rounded"],
        "dochód_IP_po_uldze_BR": tax["ip_income_after_rd"],
        "dochód_IP_kwalifikowany": tax["qualified_ip_income"],
        "dochód_IP_poza_preferencją": tax["ordinary_ip_income"],
        "podatek_IP": tax["ip_tax"],
        "podatek_NIE_finalny": tax["non_ip_tax_final"],
        "podatek_całościowy": tax["total_tax"],
        "nadpłata_lub_dopłata": signed_settlement,
        "thermomodernization_used": tax["thermomodernization_used"],
        "termomodernization_carry_over": tax["thermomodernization_carry_over"],
        "termomodernization_expired": tax["thermomodernization_expired"],
        "health_tax_credit_used": tax["health_tax_credit_used"],
        "ulga_BR_IP_wykorzystana": tax["rd_relief_ip_used"],
        "ulga_BR_NIE_wykorzystana": tax["rd_relief_non_ip_used"],
        "ulga_BR_carry_over": tax["rd_relief_carry_over"],
        "dochód_dodatkowy_skala": tax["extra_income_scale_included"],
    }


def _calculate_tax(
    input_data: dict[str, Any],
    base: dict[str, Any],
    annual_values: Mapping[str, float],
    *,
    social_in_kpir: bool,
    health_in_kpir: bool,
) -> tuple[dict[str, Any], float]:
    reliefs = input_data.get("ulgi", {}) if isinstance(input_data.get("ulgi"), dict) else {}
    social = input_data.get("zus", {}) if isinstance(input_data.get("zus"), dict) else {}
    tax = calculate_tax_for_year(
        strict_year(input_data["rok"], "input.rok"),
        non_ip_income=max(0.0, float(base["result"]["dochód_NIE"])),
        ip_income=max(0.0, float(base["result"]["dochód_IP"])),
        nexus=float(base["result"]["nexus"]),
        tax_form=str(input_data["forma_opodatkowania"]),
        previous_non_ip_business_losses=reliefs.get("strata_NIE_z_lat_poprzednich", 0),
        social_security_deduction=(
            0 if social_in_kpir else social.get("odliczenie_spoleczne_PIT", 0)
        ),
        health_income_deduction=(0 if health_in_kpir else annual_values["health_income"]),
        health_tax_credit=(0 if health_in_kpir else annual_values["health_credit"]),
        ikze=annual_values["ikze"],
        donations=reliefs.get("darowizny", 0),
        donation_limit=legacy._verified_donation_limit(reliefs),
        internet_tax_relief=reliefs.get("ulga_internet", 0),
        rehabilitative_relief_income=reliefs.get("ulga_rehabilitacyjna", 0),
        rd_relief_non_ip=reliefs.get("ulga_BR_NIE", 0),
        rd_relief_ip=reliefs.get("ulga_BR_IP", 0),
        rd_relief_limit=reliefs.get("ulga_BR_limit_odliczenia", 0),
        thermomodernization_pool=(
            0
            if reliefs.get("termomodernizacja_loty") is not None
            else reliefs.get("termomodernizacja_pula", 0)
        ),
        thermomodernization_lots=reliefs.get("termomodernizacja_loty"),
        child_tax_credit=reliefs.get("ulga_prorodzinna", 0),
        extra_income_scale=input_data.get("dochody_dodatkowe_skala", 0),
    )
    advances = number(
        (input_data.get("zaliczki") or {}).get("suma", 0)
        if isinstance(input_data.get("zaliczki"), dict)
        else 0,
        "zaliczki.suma",
    )
    settlement = calculate_overpayment(tax["total_tax"], advances)
    signed = (
        float(settlement["amount"])
        if settlement["type"] == "overpayment"
        else -float(settlement["amount"])
    )
    return tax, signed


def _reconcile_tax_fields(
    reconciliation: Mapping[str, Any] | None,
    tax: Mapping[str, Any],
    signed_settlement: float,
) -> tuple[list[str], bool, bool]:
    if reconciliation is None:
        return [], False, False
    warnings: list[str] = []
    claimed_thermo = _first(
        reconciliation,
        "termomodernizacja_odliczona",
        "thermomodernization_used",
    )
    claimed_total_tax = _first(
        reconciliation,
        "podatek_łączny",
        "podatek_laczny",
        "total_tax",
    )
    claimed_overpayment = _first(
        reconciliation,
        "nadpłata",
        "nadplata",
        "overpayment",
    )
    relief_adjustment_required = False
    if (
        claimed_thermo is not None
        and abs(
            number(claimed_thermo, "uzgodnienie.termomodernizacja")
            - float(tax["thermomodernization_used"])
        )
        > 0.01
    ):
        warnings.append("RETURN_THERMOMODERNIZATION_MISMATCH")
        relief_adjustment_required = True
    if (
        claimed_total_tax is not None
        and abs(number(claimed_total_tax, "uzgodnienie.total_tax") - float(tax["total_tax"])) > 0.01
    ):
        warnings.append("RETURN_TOTAL_TAX_MISMATCH")
    if (
        claimed_overpayment is not None
        and abs(number(claimed_overpayment, "uzgodnienie.overpayment") - signed_settlement) > 0.01
    ):
        warnings.append("RETURN_OVERPAYMENT_MISMATCH")
    tax_unchanged_only_if_reliefs_updated = bool(
        relief_adjustment_required
        and claimed_total_tax is not None
        and abs(number(claimed_total_tax, "uzgodnienie.total_tax") - float(tax["total_tax"]))
        <= 0.01
    )
    return warnings, relief_adjustment_required, tax_unchanged_only_if_reliefs_updated


def _recompute_kpir_balance_test(input_data: Mapping[str, Any]) -> str | None:
    """Reconcile KPiR totals including both signs of FX exchange differences."""
    summary = input_data.get("podsumowanie_kpir")
    if not isinstance(summary, Mapping):
        return None
    revenue = Decimal("0")
    costs = Decimal("0")
    for month in input_data.get("miesiace", []) or []:
        if not isinstance(month, dict):
            continue
        for invoice in month_invoices(month):
            revenue += money(invoice_amount(invoice))
            fx_difference = legacy._invoice_fx_difference(invoice)
            if fx_difference > 0:
                revenue += fx_difference
            elif fx_difference < 0:
                costs += -fx_difference
        for cost in month.get("koszty", []) or []:
            if isinstance(cost, Mapping):
                costs += money(number(cost.get("kwota", 0), "cost.kwota"))
    revenue_matches = abs(revenue - money(summary.get("przychody", 0))) <= Decimal("1.00")
    costs_match = abs(costs - money(summary.get("koszty", 0))) <= Decimal("1.00")
    return "PASS" if revenue_matches and costs_match else "FAIL"


def compute_reference(scenario: dict[str, Any]) -> dict[str, Any]:
    scenario = normalize_known_non_deductible_costs(scenario)
    validate_scenario(scenario)
    transformed, shares, method = prepare_scenario(scenario)
    base = legacy.compute_reference(legacy_safe_copy(transformed, for_validation=False))
    for row in base.get("monthly_W", []):
        month = str(row.get("miesiąc", ""))
        if method != "conditional_product" and month in shares:
            row["wartość"] = round(shares[month] * 100, 2)

    input_data = scenario["input"]
    original_mix = input_data.get("polityka_alokacji", {}).get("koszty_MIX", {})
    if original_mix.get("metoda") == "przychodowa_w_dacie_kosztu":
        base["result"]["klucz_MIX"]["metoda"] = "przychodowa_w_dacie_kosztu"
        base["result"]["klucz_MIX"]["wartość"] = None
        for record in base.get("classifications", []):
            if record.get("basket") == "MIX":
                record["allocation_method"] = "przychodowa_w_dacie_kosztu"
        base["tests"]["TEST_7"] = "PASS"

    try:
        source_ledger_audit, cost_warnings = apply_cost_audit(scenario, base)
    except ValueError as exc:
        raise ScenarioError(str(exc)) from exc
    base["source_ledger_audit"] = source_ledger_audit
    kpir_test = _recompute_kpir_balance_test(input_data)
    if kpir_test is not None:
        base["tests"]["TEST_1"] = kpir_test

    extra_facts, audit_codes = audit_facts(scenario, base, method)
    annual_facts, annual_values, violations = year_facts(scenario)
    facts = {**base.get("decision_facts", {}), **extra_facts, **annual_facts}
    facts["source_kpir_requires_correction"] = (
        source_ledger_audit["status"] == "REQUIRES_CORRECTION"
    )
    facts["nexus_evidence_missing"] = "NEXUS_EVIDENCE_MISSING" in {
        *cost_warnings,
        *base.get("stops_reviews", {}).get("warnings", []),
    }
    social = input_data.get("zus", {}) if isinstance(input_data.get("zus"), dict) else {}
    try:
        health_in_kpir = (
            strict_bool(social["zdrowotna_w_KPiR"], "input.zus.zdrowotna_w_KPiR")
            if "zdrowotna_w_KPiR" in social
            else False
        )
    except ValueError as exc:
        raise ScenarioError(str(exc)) from exc
    social_in_kpir = str(social.get("sposob", "brak")) == "w_KPiR"
    if health_in_kpir and (annual_values["health_income"] or annual_values["health_credit"]):
        facts["health_contribution_double_counted"] = True
    if social_in_kpir and number(social.get("odliczenie_spoleczne_PIT", 0), "zus.social") > 0:
        facts["social_contributions_double_counted"] = True

    preliminary_stops, _ = derive_decision_codes(facts)
    tax: dict[str, Any] | None = None
    signed_settlement: float | None = None
    tax_warnings: list[str] = []
    relief_adjustment_required = False
    tax_unchanged_only_if_reliefs_updated = False
    if not preliminary_stops or preliminary_stops <= CORRECTION_ONLY_STOPS:
        tax, signed_settlement = _calculate_tax(
            input_data,
            base,
            annual_values,
            social_in_kpir=social_in_kpir,
            health_in_kpir=health_in_kpir,
        )
        reconciliation = input_data.get("uzgodnienie_zeznania")
        tax_warnings, relief_adjustment_required, tax_unchanged_only_if_reliefs_updated = (
            _reconcile_tax_fields(
                reconciliation if isinstance(reconciliation, Mapping) else None,
                tax,
                signed_settlement,
            )
        )
        if tax_warnings:
            facts["return_ledger_reconciliation_failed"] = True

    stops, reviews = derive_decision_codes(facts)
    correction_related = bool(stops & CORRECTION_ONLY_STOPS)
    reconciliation_present = isinstance(input_data.get("uzgodnienie_zeznania"), Mapping)
    base["correction_preview"] = {
        "status": "UNAVAILABLE"
        if tax is None
        else ("AVAILABLE" if correction_related else "NOT_NEEDED"),
        "source_kpir_correction_required": facts["source_kpir_requires_correction"],
        "return_correction_required": bool(
            reconciliation_present
            and (facts["source_kpir_requires_correction"] or "STOP_12" in stops)
        ),
        "relief_adjustment_required": relief_adjustment_required,
        "tax_unchanged_only_if_reliefs_updated": tax_unchanged_only_if_reliefs_updated,
        "corrected_total_tax": float(tax["total_tax"]) if tax is not None else None,
        "corrected_overpayment": signed_settlement,
        "thermomodernization_used": (
            float(tax["thermomodernization_used"]) if tax is not None else None
        ),
        "thermomodernization_carry_over": (
            float(tax["thermomodernization_carry_over"]) if tax is not None else None
        ),
    }

    base["decision_facts"] = facts
    base["stops_reviews"]["stops"] = sorted(stops)
    base["stops_reviews"]["reviews"] = sorted(reviews)
    base["stops_reviews"]["warnings"] = sorted(
        set(base["stops_reviews"].get("warnings", []))
        | set(audit_codes)
        | set(violations)
        | set(cost_warnings)
        | set(tax_warnings)
    )
    if stops:
        base["status"] = "STOPPED"
        zero_after_stop(base)
        return base

    assert tax is not None and signed_settlement is not None
    base["result"]["podatek"] = _tax_result(tax, signed_settlement)
    base["tests"]["TEST_4"] = (
        "PASS"
        if tax["ordinary_base_rounded"] >= 0 and tax["thermomodernization_carry_over"] >= 0
        else "FAIL"
    )
    base["tests"]["TEST_5"] = (
        "PASS" if tax["ip_tax"] == tax_round(float(tax["ip_base_rounded"]) * 0.05) else "FAIL"
    )
    expected_total = tax_round(
        float(tax["non_ip_tax_final"]) + float(tax["ip_tax"]) - float(tax["health_tax_credit_used"])
    )
    base["tests"]["TEST_6"] = "PASS" if tax["total_tax"] == expected_total else "FAIL"
    base["status"] = "FINAL"
    return base
