"""Independent deterministic oracle for LLM scenario evaluation."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from itertools import pairwise
from typing import Any

from python_helper.ipbox_calculator import (
    AllocationPolicy,
    CostItem,
    aggregate_nexus_costs,
    aggregate_w_multiproject,
    allocate_multi_ip,
    allocate_revenue_monthly,
    calculate_nexus,
    calculate_overpayment,
    calculate_w_coefficient,
    canonical_basket,
    classify_cost,
    money,
    tax_cascade,
    tax_round,
)


class ScenarioError(ValueError):
    """Raised when a scenario contract is incomplete or contradictory."""


STOP_FACT_TO_CODE = {
    "unsupported_tax_form": "STOP_01",
    "claimed_ip_without_qualified_right": "STOP_02",
    "no_qualifying_ip_income_after_complete_evidence": "STOP_03",
    "rd_work_absent": "STOP_04",
    "ip_claim_without_required_records": "STOP_08",
    "social_contributions_double_counted": "ZUS_DOUBLE_DIP",
    "health_contribution_double_counted": "HEALTH_DOUBLE_DIP",
}

REVIEW_FACT_TO_CODE = {
    "w_above_95": "REVIEW_01",
    "w_below_50": "REVIEW_02",
    "multiple_projects_or_ips": "REVIEW_04",
    "w_jump_above_30pp": "REVIEW_08",
    "single_positive_revenue_client": "REVIEW_09",
    "uses_kis_interpretation": "REVIEW_16",
    "kis_implementation_requires_confirmation": "REVIEW_17",
}
MONTH_ID_PATTERN = re.compile(r"^(?P<year>\d{4})-(?P<month>0[1-9]|1[0-2])$")


def derive_decision_codes(decision_facts: dict[str, bool]) -> tuple[set[str], set[str]]:
    """Map atomic, pre-STOP facts to the canonical STOP and REVIEW code sets."""
    stops = {code for fact, code in STOP_FACT_TO_CODE.items() if decision_facts.get(fact) is True}
    reviews = {
        code for fact, code in REVIEW_FACT_TO_CODE.items() if decision_facts.get(fact) is True
    }
    return stops, reviews


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioError(f"{name} must be a mapping")
    return value


def _list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ScenarioError(f"{name} must be a list")
    return value


def _number(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ScenarioError(f"{name} must be numeric") from exc
    return result


def _month_evidence(month: dict[str, Any]) -> dict[str, Any] | None:
    value = month.get("ewidencja")
    if isinstance(value, dict):
        return value
    direct_keys = {"godziny_pracy", "godziny_nie_IP", "procent_faktury_IP"}
    if direct_keys & month.keys():
        return {
            "godziny_pracy": month.get("godziny_pracy"),
            "godziny_nie_IP": month.get("godziny_nie_IP", 0),
            "procent_faktury_IP": month.get("procent_faktury_IP", 100),
            "projekty": month.get("projekty", []),
        }
    return None


def _month_invoices(month: dict[str, Any]) -> list[dict[str, Any]]:
    invoices = month.get("faktury")
    if isinstance(invoices, list):
        return [dict(item) for item in invoices if isinstance(item, dict)]
    if "przychody" in month:
        return [
            {
                "kwota_PLN": month["przychody"],
                "kwalifikuje_IP": month.get("kwalifikuje_IP", False),
                "kontrahent": month.get("kontrahent", "default"),
            }
        ]
    return []


def _strict_date(value: Any, name: str) -> datetime:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise ScenarioError(f"{name} must use YYYY-MM-DD") from exc


def _invoice_amount(invoice: dict[str, Any]) -> float:
    if "kwota_waluta" in invoice:
        amount_currency = _number(invoice["kwota_waluta"], "invoice.kwota_waluta")
        if amount_currency < 0:
            raise ScenarioError("invoice.kwota_waluta must be non-negative")
        currency = str(invoice.get("waluta", "")).upper()
        if not re.fullmatch(r"[A-Z]{3}", currency) or currency == "PLN":
            raise ScenarioError("FX invoice.waluta must be a non-PLN three-letter ISO code")
        issue = _strict_date(invoice.get("data_wystawienia"), "invoice.data_wystawienia")
        payment = _strict_date(invoice.get("data_zaplaty"), "invoice.data_zaplaty")
        if payment < issue:
            raise ScenarioError("invoice.data_zaplaty cannot be earlier than data_wystawienia")
        revenue_rate = _number(invoice.get("kurs_przychodu"), "invoice.kurs_przychodu")
        payment_rate = _number(invoice.get("kurs_zaplaty"), "invoice.kurs_zaplaty")
        if revenue_rate <= 0 or payment_rate <= 0:
            raise ScenarioError("FX invoice rates must be positive")
        _strict_date(invoice.get("data_kursu_przychodu"), "invoice.data_kursu_przychodu")
        _strict_date(invoice.get("data_kursu_zaplaty"), "invoice.data_kursu_zaplaty")
        if not str(invoice.get("źródło_kursu", "")).strip():
            raise ScenarioError("FX invoice requires źródło_kursu")
        return float(money(amount_currency * revenue_rate))
    for key in ("kwota_PLN", "kwota_netto", "base_revenue_pln", "kwota"):
        if key in invoice:
            amount = _number(invoice[key], f"invoice.{key}")
            if amount < 0:
                raise ScenarioError(f"invoice.{key} must be non-negative")
            return amount
    raise ScenarioError(
        "invoice requires kwota_PLN/kwota_netto/base_revenue_pln or complete FX fields"
    )


def _invoice_fx_difference(invoice: dict[str, Any]) -> Decimal:
    if "kwota_waluta" not in invoice:
        return Decimal("0")
    amount_currency = Decimal(str(_number(invoice["kwota_waluta"], "invoice.kwota_waluta")))
    revenue_rate = Decimal(str(_number(invoice["kurs_przychodu"], "invoice.kurs_przychodu")))
    payment_rate = Decimal(str(_number(invoice["kurs_zaplaty"], "invoice.kurs_zaplaty")))
    return money(amount_currency * (payment_rate - revenue_rate))


def _private_description(description: str) -> bool:
    lowered = description.lower()
    return any(
        word in lowered
        for word in (
            "prywatn",
            "osobist",
            "do domu",
            "kawa",
            "obiad",
            "fryzjer",
            "odzież",
            "buty",
            "luxmed",
            "medicover",
        )
    )


def validate_scenario(scenario: dict[str, Any]) -> None:
    """Validate the static scenario contract before any model is called."""
    meta = _mapping(scenario.get("meta"), "meta")
    input_data = _mapping(scenario.get("input"), "input")
    assertions = _mapping(scenario.get("assertions"), "assertions")
    if not str(meta.get("id", "")).strip():
        raise ScenarioError("meta.id is required")
    if not str(meta.get("name", "")).strip():
        raise ScenarioError("meta.name is required")
    if "rok" not in input_data:
        raise ScenarioError("input.rok is required")
    try:
        year = int(input_data["rok"])
    except (TypeError, ValueError) as exc:
        raise ScenarioError("input.rok must be an integer year") from exc
    if "forma_opodatkowania" not in input_data:
        raise ScenarioError("input.forma_opodatkowania is required")
    if not assertions:
        raise ScenarioError("assertions must be non-empty")
    policy = _mapping(input_data.get("polityka_alokacji"), "input.polityka_alokacji")
    revenue = _mapping(policy.get("przychody"), "policy.przychody")
    mix = _mapping(policy.get("koszty_MIX"), "policy.koszty_MIX")
    if revenue.get("metoda") not in {
        "dokumentowa",
        "czasowa_W",
        "produktowa",
        "z_interpretacji",
        "custom",
    }:
        raise ScenarioError("unsupported revenue policy")
    AllocationPolicy(
        policy_id=str(policy.get("policy_id", meta["id"])),
        revenue_method=str(revenue["metoda"]),
        mix_method=str(mix.get("metoda", "przychodowa_roczna")),
        mix_key=mix.get("klucz"),
        source=str(mix.get("źródło", "domyślna_wizard")),
        justification=str(mix.get("uzasadnienie", "")),
    )
    reliefs = input_data.get("ulgi", {})
    if reliefs is None:
        reliefs = {}
    reliefs = _mapping(reliefs, "input.ulgi")
    relief_verification = reliefs.get("weryfikacja", {})
    if relief_verification is None:
        relief_verification = {}
    relief_verification = _mapping(relief_verification, "input.ulgi.weryfikacja")
    for key, value in reliefs.items():
        if key == "weryfikacja":
            continue
        if _number(value, f"input.ulgi.{key}") < 0:
            raise ScenarioError(f"input.ulgi.{key} must be non-negative")
    for key in ("darowizny", "ulga_internet", "ulga_rehabilitacyjna", "ulga_prorodzinna"):
        if _number(reliefs.get(key, 0), f"input.ulgi.{key}") <= 0:
            continue
        record = _mapping(relief_verification.get(key), f"input.ulgi.weryfikacja.{key}")
        if record.get("zweryfikowana") is not True:
            raise ScenarioError(f"input.ulgi.{key} requires zweryfikowana=true")
        if not str(record.get("kategoria", "")).strip():
            raise ScenarioError(f"input.ulgi.{key} requires a verified category")
        if not str(record.get("dowod", "")).strip():
            raise ScenarioError(f"input.ulgi.{key} requires an evidence reference")
    if _number(reliefs.get("ulga_BR", 0), "input.ulgi.ulga_BR") > 0:
        raise ScenarioError(
            "input.ulgi.ulga_BR is ambiguous; use ulga_BR_IP and/or ulga_BR_NIE "
            "after documenting which qualified costs led to the IP"
        )
    if _number(reliefs.get("straty_poprzednie", 0), "input.ulgi.straty_poprzednie") > 0:
        raise ScenarioError(
            "input.ulgi.straty_poprzednie is ambiguous; use "
            "strata_NIE_z_lat_poprzednich. Losses of qualified IP require a "
            "separate per-IP ledger and are not inferred by this aggregate oracle"
        )
    if _number(input_data.get("dochody_dodatkowe_skala", 0), "input.dochody_dodatkowe_skala") < 0:
        raise ScenarioError("input.dochody_dodatkowe_skala must be non-negative")

    if "zus" in input_data and input_data["zus"] is not None:
        social = _mapping(input_data["zus"], "input.zus")
        for key in ("odliczenie_spoleczne_PIT", "odliczenie_zdrowotne_PIT"):
            if _number(social.get(key, 0), f"input.zus.{key}") < 0:
                raise ScenarioError(f"input.zus.{key} must be non-negative")
    if "zaliczki" in input_data and input_data["zaliczki"] is not None:
        advances = _mapping(input_data["zaliczki"], "input.zaliczki")
        if _number(advances.get("suma", 0), "input.zaliczki.suma") < 0:
            raise ScenarioError("input.zaliczki.suma must be non-negative")

    clients = input_data.get("kontrahenci", [])
    if clients is None:
        raise ScenarioError("input.kontrahenci must be a list, not null")
    for index, client in enumerate(_list(clients, "input.kontrahenci")):
        _mapping(client, f"input.kontrahenci[{index}]")

    multi_ip = input_data.get("alokacja_multi_ip")
    if multi_ip is not None:
        multi_ip = _mapping(multi_ip, "input.alokacja_multi_ip")
        for key in (
            "koszty_wspólne_MIX",
            "przychody_software_IP",
            "przychody_całkowite",
            "przychody_IP",
        ):
            if key not in multi_ip:
                raise ScenarioError(f"input.alokacja_multi_ip.{key} is required")
        _mapping(multi_ip["przychody_IP"], "input.alokacja_multi_ip.przychody_IP")

    rd_evidence = {"IP": Decimal("0"), "NIE": Decimal("0")}
    months = _list(input_data.get("miesiace", []), "input.miesiace")
    seen_months: set[str] = set()
    for index, raw_month in enumerate(months):
        month = _mapping(raw_month, f"month[{index}]")
        month_id = str(month.get("miesiac", ""))
        if not month_id:
            raise ScenarioError(f"month[{index}].miesiac is required")
        match = MONTH_ID_PATTERN.fullmatch(month_id)
        if match is None:
            raise ScenarioError(f"month[{index}].miesiac must use strict YYYY-MM with month 01-12")
        if int(match.group("year")) != year:
            raise ScenarioError(f"month[{index}].miesiac year must match input.rok={year}")
        if month_id in seen_months:
            raise ScenarioError(f"duplicate month {month_id}")
        seen_months.add(month_id)

        if "faktury" in month:
            invoices = _list(month["faktury"], f"month[{index}].faktury")
            for item_index, invoice in enumerate(invoices):
                invoice = _mapping(invoice, f"month[{index}].faktury[{item_index}]")
                _invoice_amount(invoice)
        if "koszty" in month:
            costs = _list(month["koszty"], f"month[{index}].koszty")
            for item_index, raw_cost in enumerate(costs):
                cost = _mapping(raw_cost, f"month[{index}].koszty[{item_index}]")
                amount = _number(cost.get("kwota"), f"month[{index}].koszty[{item_index}].kwota")
                if amount < 0:
                    raise ScenarioError(
                        f"month[{index}].koszty[{item_index}].kwota must be non-negative"
                    )
                explicit_basket = str(cost.get("koszyk", cost.get("kategoria", ""))).upper()
                if explicit_basket == "IP" and not str(cost.get("allocation_source", "")).strip():
                    raise ScenarioError(
                        "IP cost requires allocation_source proving exclusive attribution"
                    )
                rd_bucket = cost.get("br_relief_bucket")
                if rd_bucket is not None:
                    rd_bucket = str(rd_bucket).upper()
                    if rd_bucket not in rd_evidence:
                        raise ScenarioError("br_relief_bucket must be IP or NIE")
                    if (rd_bucket == "IP" and explicit_basket != "IP") or (
                        rd_bucket == "NIE" and explicit_basket not in {"NON", "NIE"}
                    ):
                        raise ScenarioError("B+R relief bucket must match the cost income basket")
                    rd_amount = _number(
                        cost.get("br_relief_amount"),
                        f"month[{index}].koszty[{item_index}].br_relief_amount",
                    )
                    if rd_amount <= 0 or rd_amount > amount:
                        raise ScenarioError(
                            "br_relief_amount must be positive and cannot exceed cost"
                        )
                    if not str(cost.get("br_evidence", "")).strip():
                        raise ScenarioError("B+R qualified cost requires br_evidence")
                    rd_evidence[rd_bucket] += money(rd_amount)
        evidence = month.get("ewidencja")
        if evidence is not None:
            evidence = _mapping(evidence, f"month[{index}].ewidencja")
            projects = evidence.get("projekty", [])
            if projects is not None:
                for project_index, project in enumerate(
                    _list(projects, f"month[{index}].ewidencja.projekty")
                ):
                    _mapping(
                        project,
                        f"month[{index}].ewidencja.projekty[{project_index}]",
                    )

    requested_rd_ip = money(_number(reliefs.get("ulga_BR_IP", 0), "input.ulgi.ulga_BR_IP"))
    requested_rd_non = money(_number(reliefs.get("ulga_BR_NIE", 0), "input.ulgi.ulga_BR_NIE"))
    if requested_rd_ip > rd_evidence["IP"]:
        raise ScenarioError("ulga_BR_IP exceeds documented IP-qualified B+R costs")
    if requested_rd_non > rd_evidence["NIE"]:
        raise ScenarioError("ulga_BR_NIE exceeds documented non-IP B+R costs")


def compute_reference(scenario: dict[str, Any]) -> dict[str, Any]:
    """Compute the expected full model output from scenario input."""
    validate_scenario(scenario)
    scenario = deepcopy(scenario)
    meta = scenario["meta"]
    input_data = scenario["input"]
    year = int(input_data["rok"])
    tax_form = str(input_data["forma_opodatkowania"])
    policy_data = input_data["polityka_alokacji"]
    revenue_policy = policy_data["przychody"]
    mix_policy = policy_data["koszty_MIX"]
    policy = AllocationPolicy(
        policy_id=str(policy_data.get("policy_id", meta["id"])),
        revenue_method=str(revenue_policy["metoda"]),
        mix_method=str(mix_policy.get("metoda", "przychodowa_roczna")),
        mix_key=mix_policy.get("klucz"),
        source=str(mix_policy.get("źródło", "domyślna_wizard")),
        justification=str(mix_policy.get("uzasadnienie", "")),
    )
    reliefs = input_data.get("ulgi", {}) or {}

    warnings: set[str] = set()
    unsupported_tax_form = tax_form not in {"liniowy_19%", "skala"}
    claimed_ip_without_qualified_right = False
    rd_work_absent = False
    ip_claim_without_required_records = False
    social_contributions_double_counted = False
    health_contribution_double_counted = False

    clients = {
        str(client.get("nazwa")): bool(client.get("klauzula_IP", False))
        for client in input_data.get("kontrahenci", [])
        if isinstance(client, dict) and client.get("nazwa")
    }
    client_revenue: dict[str, Decimal] = {}
    month_w: list[dict[str, Any]] = []
    month_w_map: dict[str, float] = {}
    valid_w_values: list[float] = []
    invoices_by_month: dict[str, list[dict[str, Any]]] = {}
    positive_ip_claim = False
    has_multiple_projects = False
    raw_multi_ip = input_data.get("alokacja_multi_ip")
    has_multiple_ips = (
        isinstance(raw_multi_ip, dict)
        and isinstance(raw_multi_ip.get("przychody_IP"), dict)
        and len(raw_multi_ip["przychody_IP"]) > 1
    )

    for raw_month in input_data.get("miesiace", []):
        month = _mapping(raw_month, "month")
        month_id = str(month["miesiac"])
        invoices = _month_invoices(month)
        invoices_by_month[month_id] = invoices
        eligible_amount = Decimal("0")
        for invoice in invoices:
            amount = money(_invoice_amount(invoice))
            client = str(invoice.get("kontrahent", "default"))
            client_revenue[client] = client_revenue.get(client, Decimal("0")) + amount
            eligible = bool(invoice.get("kwalifikuje_IP", clients.get(client, False)))
            if eligible:
                eligible_amount += amount
                positive_ip_claim = positive_ip_claim or amount > 0

        evidence = _month_evidence(month)
        valid_w = False
        if month.get("brak_ewidencji") is True or (evidence is None and eligible_amount > 0):
            ip_claim_without_required_records = True
            value = 0.0
        elif month.get("brak_prac_br") is True:
            rd_work_absent = True
            value = 0.0
        elif evidence is None:
            value = 0.0
        else:
            work_hours = _number(evidence.get("godziny_pracy", 0), "godziny_pracy")
            non_ip_hours = _number(evidence.get("godziny_nie_IP", 0), "godziny_nie_IP")
            invoice_percentage = _number(
                evidence.get("procent_faktury_IP", 100),
                "procent_faktury_IP",
            )
            result = calculate_w_coefficient(work_hours, non_ip_hours, invoice_percentage)
            if result.get("status") == "ERROR":
                raise ScenarioError(f"{month_id}: {result.get('message', 'invalid W evidence')}")
            value = float(result["W"])
            valid_w = True
            projects = evidence.get("projekty")
            if isinstance(projects, list) and len(projects) > 1:
                has_multiple_projects = True
                weighted_projects: list[dict[str, float]] = []
                for project_index, raw_project in enumerate(projects):
                    project = _mapping(raw_project, f"project[{project_index}]")
                    project_hours = _number(project.get("godziny", 0), "project.godziny")
                    project_non_ip = _number(
                        project.get("godziny_nie_IP", 0), "project.godziny_nie_IP"
                    )
                    project_result = calculate_w_coefficient(project_hours, project_non_ip)
                    if project_result.get("status") == "ERROR":
                        raise ScenarioError(
                            f"{month_id} project[{project_index}]: "
                            f"{project_result.get('message', 'invalid W evidence')}"
                        )
                    weighted_projects.append(
                        {
                            "revenue": _number(project.get("przychod", 0), "project.przychod"),
                            "W": float(project_result["W"]),
                        }
                    )
                value = aggregate_w_multiproject(weighted_projects)
        month_w.append({"miesiąc": month_id, "wartość": value})
        month_w_map[month_id] = value
        if valid_w:
            valid_w_values.append(value)

    w_values = valid_w_values

    if positive_ip_claim and not input_data.get("kwalifikowane_IP", True):
        claimed_ip_without_qualified_right = True

    annual_ip_revenue = Decimal("0")
    annual_non_revenue = Decimal("0")
    fx_non_cost = Decimal("0")
    for raw_month in input_data.get("miesiace", []):
        month = _mapping(raw_month, "month")
        month_id = str(month["miesiac"])
        w_key = Decimal(str(month_w_map.get(month_id, 0.0) / 100))
        for invoice in invoices_by_month[month_id]:
            amount = money(_invoice_amount(invoice))
            client = str(invoice.get("kontrahent", "default"))
            eligible = bool(invoice.get("kwalifikuje_IP", clients.get(client, False)))
            if not eligible:
                annual_non_revenue += amount
                continue
            method = str(revenue_policy["metoda"])
            key = revenue_policy.get("klucz")
            if method == "czasowa_W":
                key = float(w_key)
            try:
                allocation = allocate_revenue_monthly(
                    float(amount),
                    method,
                    revenue_key=key,
                    document_split_ip=(
                        float(money(invoice.get("kwota_IP", amount)))
                        if method == "dokumentowa"
                        else None
                    ),
                )
            except ValueError as exc:
                raise ScenarioError(str(exc)) from exc
            ip_amount = money(allocation["ip_revenue"])
            annual_ip_revenue += ip_amount
            annual_non_revenue += amount - ip_amount

        if "różnica_kursowa" in month:
            raise ScenarioError(
                "manual różnica_kursowa is not accepted; provide source-currency invoice fields"
            )
        for invoice in invoices_by_month[month_id]:
            fx = _invoice_fx_difference(invoice)
            if fx >= 0:
                annual_non_revenue += fx
            else:
                fx_non_cost += -fx

    social = input_data.get("zus", {}) if isinstance(input_data.get("zus"), dict) else {}
    social_method = str(social.get("sposob", "brak"))
    social_in_kpir = social_method == "w_KPiR"
    health_in_kpir = bool(social.get("zdrowotna_w_KPiR", False))
    social_pit_deduction = _number(social.get("odliczenie_spoleczne_PIT", 0), "ZUS deduction")
    health_pit_deduction = _number(social.get("odliczenie_zdrowotne_PIT", 0), "health deduction")
    social_contributions_double_counted = social_in_kpir and social_pit_deduction > 0
    health_contribution_double_counted = health_in_kpir and health_pit_deduction > 0
    other_stop_condition = any(
        (
            unsupported_tax_form,
            claimed_ip_without_qualified_right,
            rd_work_absent,
            ip_claim_without_required_records,
            social_contributions_double_counted,
            health_contribution_double_counted,
        )
    )
    decision_facts = {
        "unsupported_tax_form": unsupported_tax_form,
        "claimed_ip_without_qualified_right": claimed_ip_without_qualified_right,
        "no_qualifying_ip_income_after_complete_evidence": (
            annual_ip_revenue == 0 and not other_stop_condition
        ),
        "rd_work_absent": rd_work_absent,
        "ip_claim_without_required_records": ip_claim_without_required_records,
        "social_contributions_double_counted": social_contributions_double_counted,
        "health_contribution_double_counted": health_contribution_double_counted,
        "w_above_95": bool(w_values) and max(w_values) > 95,
        "w_below_50": bool(w_values) and min(w_values) < 50,
        "multiple_projects_or_ips": has_multiple_projects or has_multiple_ips,
        "w_jump_above_30pp": any(abs(left - right) > 30 for left, right in pairwise(w_values)),
        "single_positive_revenue_client": (
            len([amount for amount in client_revenue.values() if amount > 0]) == 1
        ),
        "uses_kis_interpretation": policy.source == "interpretacja_KIS",
        "kis_implementation_requires_confirmation": policy.source == "interpretacja_KIS",
    }
    stops, reviews = derive_decision_codes(decision_facts)

    # Once the scenario is ineligible or fatally incomplete, keep the STOP report
    # deterministic instead of cascading into tax-form-specific relief errors.
    if not stops:
        if health_pit_deduction > 0 and tax_form != "liniowy_19%":
            raise ScenarioError("health PIT deduction is supported only for linear tax")
        health_limits = {2025: 12_900.0, 2026: 14_100.0}
        health_limit = health_limits.get(year)
        if health_pit_deduction > 0 and health_limit is None:
            raise ScenarioError(
                f"no verified health-contribution deduction limit for {year}; "
                "update the legal constants before calculating"
            )
        if health_limit is not None and health_pit_deduction > health_limit:
            raise ScenarioError(
                f"health PIT deduction exceeds the {year} limit of {health_limit:.2f} PLN"
            )
        ikze = _number(reliefs.get("ikze", reliefs.get("IKZE", 0)), "input.ulgi.ikze")
        ikze_limits_business = {2025: 15_611.40, 2026: 16_956.0}
        ikze_limit = ikze_limits_business.get(year)
        if ikze > 0 and ikze_limit is None:
            raise ScenarioError(
                f"no verified entrepreneur IKZE limit for {year}; update legal constants "
                "before calculating"
            )
        if ikze_limit is not None and ikze > ikze_limit:
            raise ScenarioError(
                f"IKZE deduction exceeds the {year} entrepreneur limit of {ikze_limit:.2f} PLN"
            )

    all_costs: list[CostItem] = []
    declared_private_business = False
    for raw_month in input_data.get("miesiace", []):
        month = _mapping(raw_month, "month")
        for raw_cost in month.get("koszty", []):
            cost = _mapping(raw_cost, "cost")
            description = str(cost.get("opis", "")).strip()
            if not description:
                raise ScenarioError("cost.opis is required")
            amount = _number(cost.get("kwota"), "cost.kwota")
            explicit_basket = cost.get("koszyk", cost.get("kategoria", ""))
            allocation_source = str(cost.get("allocation_source", "")).strip()
            if str(explicit_basket).upper() == "IP" and not allocation_source:
                raise ScenarioError(
                    "IP cost requires allocation_source proving exclusive attribution"
                )
            item = CostItem(
                description=description,
                amount=amount,
                basket=str(explicit_basket) if explicit_basket else "",
                allocation_method=str(cost.get("allocation_method", "")),
                allocation_key=cost.get("allocation_key"),
                allocation_source=allocation_source,
                nexus_source=str(cost.get("nexus_source", "outside_nexus")),
                nexus_basket={
                    "own_br": "A",
                    "unrelated_br_contractor": "B",
                    "related_br_contractor": "C",
                    "acquired_ip": "D",
                }.get(str(cost.get("nexus_source", "")), "poza_nexus"),
                nexus_amount=cost.get("nexus_amount"),
            )
            if not item.basket:
                item = classify_cost(item, social_in_kpir, health_in_kpir)
            declared = str(cost.get("deklarowany_koszyk", explicit_basket or "")).upper()
            if _private_description(description) and declared in {"IP", "MIX", "NIE", "NON"}:
                declared_private_business = True
            all_costs.append(item)

    if fx_non_cost:
        all_costs.append(
            CostItem(
                description="Ujemna różnica kursowa",
                amount=float(fx_non_cost),
                basket="NON",
                nexus_source="outside_nexus",
                nexus_basket="poza_nexus",
            )
        )

    total_revenue = annual_ip_revenue + annual_non_revenue
    mix_total = sum(
        (money(item.amount) for item in all_costs if item.basket == "MIX"), Decimal("0")
    )
    if stops:
        mix_key: float | None = None
        mix_status = "NOT_APPLICABLE"
    elif mix_total == 0:
        mix_key = None
        mix_status = "NOT_APPLICABLE"
    elif policy.mix_method == "przychodowa_roczna":
        if total_revenue == 0:
            mix_key = None
            mix_status = "DEFERRED"
        else:
            mix_key = float(annual_ip_revenue / total_revenue)
            mix_status = "FINAL"
    else:
        assert policy.mix_key is not None
        mix_key = policy.mix_key
        mix_status = "FINAL"

    classifications: list[dict[str, Any]] = []
    annual_ip_cost = Decimal("0")
    annual_non_cost = Decimal("0")
    excluded_cost = Decimal("0")
    for item in all_costs:
        amount = money(item.amount)
        ip_amount = Decimal("0")
        non_amount = Decimal("0")
        allocation_key: float | None = None
        allocation_method = "direct"
        allocation_source = item.allocation_source
        if item.basket == "IP":
            ip_amount = amount
            allocation_key = 1.0
            annual_ip_cost += amount
        elif item.basket == "NON":
            non_amount = amount
            allocation_key = 0.0
            annual_non_cost += amount
        elif item.basket == "WYKLUCZONE":
            allocation_method = "excluded"
            excluded_cost += amount
        elif item.basket == "MIX":
            allocation_method = item.allocation_method or policy.mix_method
            allocation_source = item.allocation_source or policy.source
            allocation_key = item.allocation_key if item.allocation_key is not None else mix_key
            if allocation_key is not None:
                ip_amount = money(amount * Decimal(str(allocation_key)))
                non_amount = amount - ip_amount
                annual_ip_cost += ip_amount
                annual_non_cost += non_amount

        nexus_amount = money(item.nexus_amount if item.nexus_amount is not None else 0)
        if (
            item.nexus_basket in {"A", "B", "C", "D"}
            and item.nexus_amount is None
            and item.basket != "MIX"
        ):
            nexus_amount = amount
        classifications.append(
            {
                "opis": item.description,
                "amount": float(amount),
                "basket": canonical_basket(item.basket),
                "allocation_method": allocation_method,
                "allocation_source": allocation_source,
                "allocation_key": allocation_key,
                "ip_amount": float(ip_amount),
                "non_ip_amount": float(non_amount),
                "nexus_source": item.nexus_source,
                "nexus_basket": item.nexus_basket,
                "nexus_amount": float(nexus_amount),
            }
        )

    nexus_costs = aggregate_nexus_costs(all_costs)
    nexus_result = calculate_nexus(
        nexus_costs["A"],
        nexus_costs["B"],
        nexus_costs["C"],
        nexus_costs["D"],
    )
    nexus = float(nexus_result["nexus"])
    income_ip = float(annual_ip_revenue - annual_ip_cost)
    income_non = float(annual_non_revenue - annual_non_cost)

    if stops:
        tax = {
            "ip_base_rounded": 0,
            "non_ip_base_rounded": 0,
            "ip_tax": 0,
            "non_ip_tax_final": 0,
            "total_tax": 0,
            "thermomodernization_carry_over": 0,
            "rd_relief_ip_used": 0,
            "rd_relief_non_ip_used": 0,
            "rd_relief_carry_over": 0,
            "extra_income_scale_included": 0,
        }
    else:
        try:
            tax = tax_cascade(
                non_ip_income=income_non,
                ip_income=income_ip,
                nexus=nexus,
                tax_form=tax_form,
                previous_non_ip_business_losses=reliefs.get("strata_NIE_z_lat_poprzednich", 0),
                social_security_deduction=(0 if social_in_kpir else social_pit_deduction),
                health_contribution_deduction=(0 if health_in_kpir else health_pit_deduction),
                ikze=reliefs.get("ikze", reliefs.get("IKZE", 0)),
                donations=reliefs.get("darowizny", 0),
                internet_tax_relief=reliefs.get("ulga_internet", 0),
                rehabilitative_relief_income=reliefs.get("ulga_rehabilitacyjna", 0),
                rd_relief_non_ip=reliefs.get("ulga_BR_NIE", 0),
                rd_relief_ip=reliefs.get("ulga_BR_IP", 0),
                rd_relief_limit=reliefs.get("ulga_BR_limit_odliczenia", 0),
                thermomodernization_pool=reliefs.get("termomodernizacja_pula", 0),
                child_tax_credit=reliefs.get("ulga_prorodzinna", 0),
                extra_income_scale=input_data.get("dochody_dodatkowe_skala", 0),
            )
        except ValueError as exc:
            raise ScenarioError(str(exc)) from exc
    advances = _number(
        (input_data.get("zaliczki") or {}).get("suma", 0)
        if isinstance(input_data.get("zaliczki"), dict)
        else 0,
        "zaliczki.suma",
    )
    settlement = calculate_overpayment(tax["total_tax"], advances)
    settlement_signed = (
        float(settlement["amount"])
        if settlement["type"] == "overpayment"
        else -float(settlement["amount"])
    )

    if stops:
        income_ip = 0.0
        income_non = 0.0
        settlement_signed = 0.0

    multi_ip_result: dict[str, Any] | None = None
    multi_data = input_data.get("alokacja_multi_ip")
    if isinstance(multi_data, dict) and not stops:
        allocation = allocate_multi_ip(
            total_indirect_costs=multi_data["koszty_wspólne_MIX"],
            software_ip_revenue=multi_data["przychody_software_IP"],
            total_revenue=multi_data["przychody_całkowite"],
            ip_revenues=multi_data["przychody_IP"],
        )
        multi_ip_result = {
            "stage1_software_share": allocation["stage1_software_share"],
            "stage1_non_software_share": allocation["stage1_non_software_share"],
            "allocations": [
                {"ip": name, "amount": amount}
                for name, amount in sorted(allocation["projects"].items())
            ],
        }

    summary = input_data.get("podsumowanie_kpir")
    if isinstance(summary, dict):
        monthly_revenue = sum(
            (
                money(_invoice_amount(invoice))
                for invoices in invoices_by_month.values()
                for invoice in invoices
            ),
            Decimal("0"),
        )
        monthly_costs = sum((money(item.amount) for item in all_costs), Decimal("0"))
        test_1 = abs(monthly_revenue - money(summary.get("przychody", 0))) <= Decimal(
            "1.00"
        ) and abs(monthly_costs - money(summary.get("koszty", 0))) <= Decimal("1.00")
    else:
        test_1 = True
    test_2 = not declared_private_business
    test_3 = not ({"ZUS_DOUBLE_DIP", "HEALTH_DOUBLE_DIP"} & stops)
    test_4 = tax["non_ip_base_rounded"] >= 0 and tax.get("thermomodernization_carry_over", 0) >= 0
    expected_ip_tax = tax_round(float(tax["ip_base_rounded"]) * 0.05)
    test_5 = int(tax["ip_tax"]) == expected_ip_tax
    test_6 = int(tax["total_tax"]) == int(tax["ip_tax"]) + int(tax["non_ip_tax_final"])
    test_7 = policy.mix_method == str(mix_policy.get("metoda"))
    test_8 = all(
        not (
            record["basket"] == "MIX"
            and record["nexus_basket"] in {"A", "B", "C", "D"}
            and record["nexus_amount"] <= 0
        )
        for record in classifications
    )
    test_9 = all(
        bool(str(month.get("opis_projektu", "")).strip())
        or sum((_invoice_amount(invoice) for invoice in _month_invoices(month)), 0) == 0
        for month in input_data.get("miesiace", [])
    )
    tests = {
        f"TEST_{index}": "PASS" if value else "FAIL"
        for index, value in enumerate(
            (test_1, test_2, test_3, test_4, test_5, test_6, test_7, test_8, test_9),
            start=1,
        )
    }

    return {
        "status": "STOPPED" if stops else "FINAL",
        "result": {
            "rok": year,
            "przychody_roczne": {
                "IP": float(annual_ip_revenue if not stops else Decimal("0")),
                "NIE": float(annual_non_revenue if not stops else Decimal("0")),
            },
            "koszty_roczne": {
                "IP": float(annual_ip_cost if not stops else Decimal("0")),
                "NIE": float(annual_non_cost if not stops else Decimal("0")),
                "MIX": float(mix_total if not stops else Decimal("0")),
                "WYKLUCZONE": float(excluded_cost if not stops else Decimal("0")),
            },
            "nexus_koszty": {
                key: float(value if not stops else 0) for key, value in nexus_costs.items()
            },
            "nexus": nexus if not stops else 0.0,
            "dochód_IP": income_ip,
            "dochód_NIE": income_non,
            "klucz_MIX": {
                "metoda": policy.mix_method,
                "źródło": policy.source,
                "wartość": mix_key,
                "status": mix_status,
            },
            "alokacja_multi_ip": multi_ip_result,
            "podatek": {
                "podstawa_IP": tax["ip_base_rounded"],
                "podstawa_NIE": tax["non_ip_base_rounded"],
                "podatek_IP": tax["ip_tax"],
                "podatek_NIE_finalny": tax["non_ip_tax_final"],
                "podatek_całościowy": tax["total_tax"],
                "nadpłata_lub_dopłata": settlement_signed,
                "termomodernization_carry_over": tax.get("thermomodernization_carry_over", 0),
                "ulga_BR_IP_wykorzystana": tax.get("rd_relief_ip_used", 0),
                "ulga_BR_NIE_wykorzystana": tax.get("rd_relief_non_ip_used", 0),
                "ulga_BR_carry_over": tax.get("rd_relief_carry_over", 0),
                "dochód_dodatkowy_skala": tax.get("extra_income_scale_included", 0),
            },
        },
        "classifications": classifications if not stops else [],
        "monthly_W": month_w,
        "tests": tests,
        "stops_reviews": {
            "stops": sorted(stops),
            "reviews": sorted(reviews),
            "warnings": sorted(warnings),
        },
        "decision_facts": decision_facts,
    }
