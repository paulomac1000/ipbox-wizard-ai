"""Extended STOP facts and deterministic audit guards."""

from __future__ import annotations

from typing import Any

from python_helper.allocation_audit import (
    audit_revenue_allocation,
    reconcile_return_to_ledger,
)
from python_helper.tax_year_rules import get_tax_year_rules, strict_year, validate_year_amounts

from . import oracle_legacy as legacy
from .oracle_adapter import invoice_amount, month_evidence, month_invoices, number

ScenarioError = legacy.ScenarioError
STOP_FACT_TO_CODE = {
    **legacy.STOP_FACT_TO_CODE,
    "revenue_allocation_inconsistent": "STOP_09",
    "invoice_percentage_double_applied": "STOP_10",
    "allocation_method_changed_without_evidence": "STOP_11",
    "return_ledger_reconciliation_failed": "STOP_12",
    "rd_ip_relief_not_available_for_year": "STOP_13",
    "year_limit_exceeded": "STOP_14",
    "health_deduction_mode_invalid_for_year": "STOP_15",
    "unsupported_tax_year": "STOP_16",
    "source_kpir_requires_correction": "SOURCE_KPIR_REQUIRES_CORRECTION",
}
REVIEW_FACT_TO_CODE = {
    **legacy.REVIEW_FACT_TO_CODE,
    "nexus_evidence_missing": "REVIEW_18",
    "source_coverage_incomplete": "REVIEW_19",
    "asset_classification_requires_review": "REVIEW_20",
    "contribution_classification_requires_review": "REVIEW_21",
    "legacy_thermomodernization_pool_requires_review": "REVIEW_22",
}


def derive_decision_codes(facts: dict[str, bool]) -> tuple[set[str], set[str]]:
    stops = {code for fact, code in STOP_FACT_TO_CODE.items() if facts.get(fact) is True}
    reviews = {code for fact, code in REVIEW_FACT_TO_CODE.items() if facts.get(fact) is True}
    return stops, reviews


def _usable_allocation_evidence(month: dict[str, Any]) -> dict[str, float] | None:
    """Return normalized W evidence only when it is safe to audit.

    Missing or unusable evidence is handled by the primary oracle as STOP_08 or
    another explicit fact. The secondary allocation audit must not replace that
    deterministic STOP report with a raw ValueError.
    """
    evidence = month_evidence(month)
    if not isinstance(evidence, dict):
        return None
    work_hours = number(evidence.get("godziny_pracy", 0), "godziny_pracy")
    non_ip_hours = number(evidence.get("godziny_nie_IP", 0), "godziny_nie_IP")
    invoice_percentage = number(
        evidence.get("procent_faktury_IP", 100),
        "procent_faktury_IP",
    )
    if work_hours <= 0:
        return None
    if non_ip_hours < 0 or non_ip_hours > work_hours:
        return None
    if invoice_percentage < 0 or invoice_percentage > 100:
        return None
    return {
        "work_hours": work_hours,
        "non_ip_hours": non_ip_hours,
        "invoice_percentage": invoice_percentage,
    }


def audit_facts(
    scenario: dict[str, Any], result: dict[str, Any], method: str
) -> tuple[dict[str, bool], list[str]]:
    input_data = scenario.get("input", {})
    rows: list[dict[str, Any]] = []
    for month in input_data.get("miesiace", []) or []:
        if not isinstance(month, dict) or not isinstance(month.get("kontrola_alokacji"), dict):
            continue
        evidence = _usable_allocation_evidence(month)
        if evidence is None:
            continue
        declared = month["kontrola_alokacji"]
        ip = number(declared.get("przychod_IP"), "kontrola.przychod_IP")
        total = sum((invoice_amount(invoice) for invoice in month_invoices(month)), 0.0)
        rows.append(
            {
                "month": str(month.get("miesiac", "")),
                "total_revenue": total,
                "reported_ip_revenue": ip,
                "reported_non_ip_revenue": declared.get("przychod_NIE", total - ip),
                **evidence,
                "w_method": method,
            }
        )
    findings = audit_revenue_allocation(rows) if rows else []
    reconciliation = input_data.get("uzgodnienie_zeznania")
    if isinstance(reconciliation, dict):
        ledger = {
            "ip_revenue": result["result"]["przychody_roczne"]["IP"],
            "non_ip_revenue": result["result"]["przychody_roczne"]["NIE"],
            "ip_cost": result["result"]["koszty_roczne"]["IP"],
            "non_ip_cost": result["result"]["koszty_roczne"]["NIE"],
        }
        tax_return = {
            "ip_revenue": reconciliation.get("przychod_IP", reconciliation.get("ip_revenue", 0)),
            "non_ip_revenue": reconciliation.get(
                "przychod_NIE", reconciliation.get("non_ip_revenue", 0)
            ),
            "ip_cost": reconciliation.get("koszt_IP", reconciliation.get("ip_cost", 0)),
            "non_ip_cost": reconciliation.get("koszt_NIE", reconciliation.get("non_ip_cost", 0)),
        }
        findings.extend(reconcile_return_to_ledger(ledger, tax_return))
    codes = {finding.code for finding in findings}
    facts = {
        "revenue_allocation_inconsistent": bool(
            codes
            & {
                "REVENUE_SPLIT_DOES_NOT_BALANCE",
                "REVENUE_ALLOCATION_MISMATCH",
                "FULL_REVENUE_DESPITE_NON_IP_SHARE",
            }
        ),
        "invoice_percentage_double_applied": "INVOICE_PERCENTAGE_DOUBLE_APPLIED" in codes,
        "allocation_method_changed_without_evidence": "ALLOCATION_METHOD_SWITCH" in codes,
        "return_ledger_reconciliation_failed": any(code.startswith("RETURN_") for code in codes),
    }
    return facts, sorted(codes)


def year_facts(
    scenario: dict[str, Any],
) -> tuple[dict[str, bool], dict[str, float], list[str]]:
    input_data = scenario.get("input", {})
    year_raw = input_data.get("rok")
    unsupported = False
    try:
        year = strict_year(year_raw, "input.rok")
        get_tax_year_rules(year)
    except ValueError:
        year = year_raw if type(year_raw) is int else 0
        unsupported = True
    reliefs = input_data.get("ulgi", {}) if isinstance(input_data.get("ulgi"), dict) else {}
    social = input_data.get("zus", {}) if isinstance(input_data.get("zus"), dict) else {}
    values = {
        "ikze": number(reliefs.get("ikze", reliefs.get("IKZE", 0)), "ulgi.ikze"),
        "health_income": number(
            social.get(
                "odliczenie_zdrowotne_od_dochodu",
                social.get("odliczenie_zdrowotne_PIT", 0),
            ),
            "zus.health_income",
        ),
        "health_credit": number(
            social.get("odliczenie_zdrowotne_od_podatku", 0), "zus.health_credit"
        ),
        "rd_ip": number(reliefs.get("ulga_BR_IP", 0), "ulgi.ulga_BR_IP"),
    }
    violations: list[str] = []
    if not unsupported:
        try:
            violations = validate_year_amounts(
                year,
                ikze=values["ikze"],
                health_income_deduction=values["health_income"],
                health_tax_credit=values["health_credit"],
                rd_relief_ip=values["rd_ip"],
            )
        except ValueError as exc:
            raise ScenarioError(str(exc)) from exc
    facts = {
        "unsupported_tax_year": unsupported,
        "rd_ip_relief_not_available_for_year": "BR_IPBOX_NOT_SIMULTANEOUS" in violations,
        "year_limit_exceeded": bool(
            {"IKZE_LIMIT_EXCEEDED", "HEALTH_LIMIT_EXCEEDED"} & set(violations)
        ),
        "health_deduction_mode_invalid_for_year": "HEALTH_MODE_INVALID" in violations,
    }
    return facts, values, violations


def zero_after_stop(reference: dict[str, Any]) -> None:
    result = reference["result"]
    result["przychody_roczne"] = {"IP": 0.0, "NIE": 0.0}
    result["koszty_roczne"] = {"IP": 0.0, "NIE": 0.0, "MIX": 0.0, "WYKLUCZONE": 0.0}
    result["nexus_koszty"] = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "poza_nexus": 0.0}
    result["nexus"] = 0.0
    result["dochód_IP"] = 0.0
    result["dochód_NIE"] = 0.0
    result["klucz_MIX"]["wartość"] = None
    result["klucz_MIX"]["status"] = "NOT_APPLICABLE"
    result["alokacja_multi_ip"] = None
    result["podatek"] = {
        "podstawa_IP": 0,
        "podstawa_NIE": 0,
        "podstawa_zwykła": 0,
        "dochód_IP_po_uldze_BR": 0.0,
        "dochód_IP_kwalifikowany": 0.0,
        "dochód_IP_poza_preferencją": 0.0,
        "podatek_IP": 0,
        "podatek_NIE_finalny": 0,
        "podatek_całościowy": 0,
        "nadpłata_lub_dopłata": 0.0,
        "thermomodernization_used": 0.0,
        "termomodernization_carry_over": 0.0,
        "termomodernization_expired": 0.0,
        "thermomodernization_mode": "none",
        "thermomodernization_evidence_status": "NOT_APPLICABLE",
        "thermomodernization_rules_source_id": "MF_THERMOMODERNIZATION",
        "thermomodernization_limit": 53000.0,
        "health_tax_credit_used": 0.0,
        "ulga_BR_IP_wykorzystana": 0.0,
        "ulga_BR_NIE_wykorzystana": 0.0,
        "ulga_BR_carry_over": 0.0,
        "dochód_dodatkowy_skala": 0.0,
    }
    reference["classifications"] = []
