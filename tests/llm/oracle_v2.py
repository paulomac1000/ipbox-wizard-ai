"""Year-aware and reconciliation-aware wrapper around the stable scenario oracle."""

from __future__ import annotations

from typing import Any

from python_helper.ipbox_calculator import calculate_overpayment, tax_round
from python_helper.tax_year_rules import calculate_tax_for_year

from . import oracle as legacy
from .allocation_guard import audit_facts
from .oracle_adapter import legacy_safe_copy, number, prepare_scenario
from .oracle_guards import (
    REVIEW_FACT_TO_CODE,
    STOP_FACT_TO_CODE,
    derive_decision_codes,
    year_facts,
    zero_after_stop,
)

ScenarioError = legacy.ScenarioError

__all__ = [
    "REVIEW_FACT_TO_CODE",
    "STOP_FACT_TO_CODE",
    "ScenarioError",
    "compute_reference",
    "derive_decision_codes",
    "validate_scenario",
]


def validate_scenario(scenario: dict[str, Any]) -> None:
    transformed, _shares, _method = prepare_scenario(scenario)
    try:
        legacy.validate_scenario(legacy_safe_copy(transformed, for_validation=True))
    except legacy.ScenarioError:
        raise
    except ValueError as exc:
        raise ScenarioError(str(exc)) from exc
    year_facts(scenario)


def compute_reference(scenario: dict[str, Any]) -> dict[str, Any]:
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

    extra_facts, audit_codes = audit_facts(scenario, base, method)
    annual_facts, annual_values, violations = year_facts(scenario)
    facts = {**base.get("decision_facts", {}), **extra_facts, **annual_facts}
    social = (
        input_data.get("zus", {}) if isinstance(input_data.get("zus"), dict) else {}
    )
    health_in_kpir = bool(social.get("zdrowotna_w_KPiR", False))
    social_in_kpir = str(social.get("sposob", "brak")) == "w_KPiR"
    if health_in_kpir and (
        annual_values["health_income"] or annual_values["health_credit"]
    ):
        facts["health_contribution_double_counted"] = True
    if (
        social_in_kpir
        and number(social.get("odliczenie_spoleczne_PIT", 0), "zus.social") > 0
    ):
        facts["social_contributions_double_counted"] = True

    stops, reviews = derive_decision_codes(facts)
    base["decision_facts"] = facts
    base["stops_reviews"]["stops"] = sorted(stops)
    base["stops_reviews"]["reviews"] = sorted(reviews)
    base["stops_reviews"]["warnings"] = sorted(
        set(base["stops_reviews"].get("warnings", []))
        | set(audit_codes)
        | set(violations)
    )
    if stops:
        base["status"] = "STOPPED"
        zero_after_stop(base)
        return base

    reliefs = (
        input_data.get("ulgi", {}) if isinstance(input_data.get("ulgi"), dict) else {}
    )
    tax = calculate_tax_for_year(
        int(input_data["rok"]),
        non_ip_income=max(0.0, float(base["result"]["dochód_NIE"])),
        ip_income=max(0.0, float(base["result"]["dochód_IP"])),
        nexus=float(base["result"]["nexus"]),
        tax_form=str(input_data["forma_opodatkowania"]),
        previous_non_ip_business_losses=reliefs.get("strata_NIE_z_lat_poprzednich", 0),
        social_security_deduction=(
            0 if social_in_kpir else social.get("odliczenie_spoleczne_PIT", 0)
        ),
        health_income_deduction=(
            0 if health_in_kpir else annual_values["health_income"]
        ),
        health_tax_credit=(0 if health_in_kpir else annual_values["health_credit"]),
        ikze=annual_values["ikze"],
        donations=reliefs.get("darowizny", 0),
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
    base["result"]["podatek"] = {
        "podstawa_IP": tax["ip_base_rounded"],
        "podstawa_NIE": tax["non_ip_base_rounded"],
        "podatek_IP": tax["ip_tax"],
        "podatek_NIE_finalny": tax["non_ip_tax_final"],
        "podatek_całościowy": tax["total_tax"],
        "nadpłata_lub_dopłata": signed,
        "termomodernization_carry_over": tax["thermomodernization_carry_over"],
        "termomodernization_expired": tax["thermomodernization_expired"],
        "health_tax_credit_used": tax["health_tax_credit_used"],
        "ulga_BR_IP_wykorzystana": tax["rd_relief_ip_used"],
        "ulga_BR_NIE_wykorzystana": tax["rd_relief_non_ip_used"],
        "ulga_BR_carry_over": tax["rd_relief_carry_over"],
        "dochód_dodatkowy_skala": tax["extra_income_scale_included"],
    }
    base["tests"]["TEST_4"] = (
        "PASS"
        if tax["non_ip_base_rounded"] >= 0
        and tax["thermomodernization_carry_over"] >= 0
        else "FAIL"
    )
    base["tests"]["TEST_5"] = (
        "PASS"
        if tax["ip_tax"] == tax_round(float(tax["ip_base_rounded"]) * 0.05)
        else "FAIL"
    )
    expected_total = tax_round(
        float(tax["non_ip_tax_final"])
        + float(tax["ip_tax"])
        - float(tax["health_tax_credit_used"])
    )
    base["tests"]["TEST_6"] = "PASS" if tax["total_tax"] == expected_total else "FAIL"
    base["status"] = "FINAL"
    return base
