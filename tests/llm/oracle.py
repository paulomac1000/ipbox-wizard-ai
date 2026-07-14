"""Independent deterministic oracle for LLM scenario evaluation."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from itertools import pairwise
from typing import Any

from python_helper.ipbox_calculator import (
    AllocationPolicy,
    CostItem,
    aggregate_nexus_costs,
    aggregate_w_multiproject,
    allocate_multi_ip,
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
                "kwalifikuje_IP": month.get("kwalifikuje_IP", True),
                "kontrahent": month.get("kontrahent", "default"),
            }
        ]
    return []


def _invoice_amount(invoice: dict[str, Any]) -> float:
    for key in ("kwota_PLN", "kwota_netto", "base_revenue_pln", "kwota"):
        if key in invoice:
            return _number(invoice[key], f"invoice.{key}")
    raise ScenarioError("invoice requires kwota_PLN/kwota_netto/base_revenue_pln")


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
    months = _list(input_data.get("miesiace", []), "input.miesiace")
    seen_months: set[str] = set()
    for index, raw_month in enumerate(months):
        month = _mapping(raw_month, f"month[{index}]")
        month_id = str(month.get("miesiac", ""))
        if not month_id:
            raise ScenarioError(f"month[{index}].miesiac is required")
        if month_id in seen_months:
            raise ScenarioError(f"duplicate month {month_id}")
        seen_months.add(month_id)


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

    stops: set[str] = set()
    reviews: set[str] = set(meta.get("expected_reviews", []))
    warnings: set[str] = set()
    if tax_form not in {"liniowy_19%", "skala"}:
        stops.add("STOP_01")

    clients = {
        str(client.get("nazwa")): bool(client.get("klauzula_IP", True))
        for client in input_data.get("kontrahenci", [])
        if isinstance(client, dict) and client.get("nazwa")
    }
    client_revenue: dict[str, Decimal] = {}
    month_w: list[dict[str, Any]] = []
    month_w_map: dict[str, float] = {}
    invoices_by_month: dict[str, list[dict[str, Any]]] = {}
    positive_ip_claim = False

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
            eligible = bool(invoice.get("kwalifikuje_IP", clients.get(client, True)))
            if eligible:
                eligible_amount += amount
                positive_ip_claim = positive_ip_claim or amount > 0

        evidence = _month_evidence(month)
        if month.get("brak_ewidencji") is True or (evidence is None and eligible_amount > 0):
            stops.add("STOP_08")
            value = 0.0
        elif month.get("brak_prac_br") is True:
            stops.add("STOP_04")
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
            value = float(result["W"])
            if result["status"] == "REVIEW_01":
                reviews.add("REVIEW_01")
            if result["status"] == "REVIEW_02":
                reviews.add("REVIEW_02")
            projects = evidence.get("projekty")
            if isinstance(projects, list) and len(projects) > 1:
                weighted_projects: list[dict[str, float]] = []
                for project_index, raw_project in enumerate(projects):
                    project = _mapping(raw_project, f"project[{project_index}]")
                    project_hours = _number(project.get("godziny", 0), "project.godziny")
                    project_non_ip = _number(
                        project.get("godziny_nie_IP", 0), "project.godziny_nie_IP"
                    )
                    project_w = calculate_w_coefficient(project_hours, project_non_ip)["W"]
                    weighted_projects.append(
                        {
                            "revenue": _number(project.get("przychod", 0), "project.przychod"),
                            "W": float(project_w),
                        }
                    )
                value = aggregate_w_multiproject(weighted_projects)
                reviews.add("REVIEW_04")
        month_w.append({"miesiąc": month_id, "wartość": value})
        month_w_map[month_id] = value

    w_values = [entry["wartość"] for entry in month_w if entry["wartość"] > 0]
    if any(abs(left - right) > 30 for left, right in pairwise(w_values)):
        reviews.add("REVIEW_08")
    if len([amount for amount in client_revenue.values() if amount > 0]) == 1 and client_revenue:
        reviews.add("REVIEW_09")
    if policy.source == "interpretacja_KIS":
        reviews.update({"REVIEW_16", "REVIEW_17"})

    if positive_ip_claim and not input_data.get("kwalifikowane_IP", True):
        stops.add("STOP_02")

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
            eligible = bool(invoice.get("kwalifikuje_IP", clients.get(client, True)))
            if not eligible:
                annual_non_revenue += amount
                continue
            method = revenue_policy["metoda"]
            if method == "dokumentowa":
                ip_amount = money(invoice.get("kwota_IP", amount))
                if ip_amount > amount:
                    raise ScenarioError("invoice.kwota_IP cannot exceed invoice amount")
            else:
                key = revenue_policy.get("klucz")
                if method == "czasowa_W":
                    key = float(w_key)
                if key is None:
                    raise ScenarioError(f"revenue policy {method} requires klucz")
                ip_amount = money(amount * Decimal(str(key)))
            annual_ip_revenue += ip_amount
            annual_non_revenue += amount - ip_amount

        fx = money(month.get("różnica_kursowa", 0))
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
    if social_in_kpir and social_pit_deduction > 0:
        stops.add("ZUS_DOUBLE_DIP")
    if health_in_kpir and health_pit_deduction > 0:
        stops.add("HEALTH_DOUBLE_DIP")

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
            item = CostItem(
                description=description,
                amount=amount,
                basket=str(explicit_basket) if explicit_basket else "",
                allocation_method=str(cost.get("allocation_method", "")),
                allocation_key=cost.get("allocation_key"),
                allocation_source=str(cost.get("allocation_source", "")),
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

    if annual_ip_revenue == 0 and not stops:
        stops.add("STOP_03")

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
        allocation_source = item.allocation_source or "dokument"
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

    reliefs = input_data.get("ulgi", {}) if isinstance(input_data.get("ulgi"), dict) else {}
    tax = tax_cascade(
        non_ip_income=income_non,
        ip_income=income_ip,
        nexus=nexus,
        tax_form=tax_form if tax_form in {"liniowy_19%", "skala"} else "liniowy_19%",
        previous_losses=reliefs.get("straty_poprzednie", 0),
        social_security_deduction=social_pit_deduction,
        ikze=reliefs.get("ikze", reliefs.get("IKZE", 0)),
        donations=reliefs.get("darowizny", 0),
        internet_tax_relief=reliefs.get("ulga_internet", 0),
        rehabilitative_relief_income=reliefs.get("ulga_rehabilitacyjna", 0),
        rd_relief=reliefs.get("ulga_BR", 0),
        thermomodernization_pool=reliefs.get("termomodernizacja_pula", 0),
        child_tax_credit=reliefs.get("ulga_prorodzinna", 0),
        extra_income_scale=input_data.get("dochody_dodatkowe_skala", 0),
    )
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
        tax = {
            "ip_base_rounded": 0,
            "non_ip_base_rounded": 0,
            "ip_tax": 0,
            "non_ip_tax_final": 0,
            "total_tax": 0,
            "thermomodernization_carry_over": 0,
        }
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
    }
