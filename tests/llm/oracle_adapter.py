"""Normalize extended scenarios for the stable deterministic oracle."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

from python_helper.allocation_audit import calculate_w_share
from python_helper.ipbox_calculator import allocate_revenue_monthly, money

from . import oracle as legacy

ScenarioError = legacy.ScenarioError
W_METHOD_ALIASES = {
    "conditional_product": "conditional_product",
    "warunkowy_iloczyn": "conditional_product",
    "iloczyn": "conditional_product",
    "disjoint_components": "disjoint_components",
    "rozłączne_składniki": "disjoint_components",
    "historyczna_rozłączna": "disjoint_components",
    "time_only": "time_only",
    "tylko_czas": "time_only",
}


def number(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ScenarioError(f"{name} must be numeric") from exc
    if result != result or result in {float("inf"), float("-inf")}:
        raise ScenarioError(f"{name} must be finite")
    return result


def w_method(input_data: dict[str, Any]) -> str:
    raw: Any = input_data.get("metoda_W", "conditional_product")
    policy = input_data.get("polityka_alokacji")
    if isinstance(policy, dict) and isinstance(policy.get("W"), dict):
        raw = policy["W"].get("metoda", raw)
    normalized = W_METHOD_ALIASES.get(str(raw), str(raw))
    if normalized not in set(W_METHOD_ALIASES.values()):
        raise ScenarioError(f"unsupported W semantics {raw!r}")
    return normalized


def month_evidence(month: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(month.get("ewidencja"), dict):
        return month["ewidencja"]
    keys = {"godziny_pracy", "godziny_nie_IP", "procent_faktury_IP"}
    if not keys & month.keys():
        return None
    return {
        "godziny_pracy": month.get("godziny_pracy"),
        "godziny_nie_IP": month.get("godziny_nie_IP", 0),
        "procent_faktury_IP": month.get("procent_faktury_IP", 100),
        "projekty": month.get("projekty", []),
    }


def invoice_amount(invoice: dict[str, Any]) -> float:
    try:
        return float(legacy._invoice_amount(invoice))
    except (AttributeError, ValueError) as exc:
        raise ScenarioError(str(exc)) from exc


def month_invoices(month: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return legacy._month_invoices(month)
    except AttributeError as exc:  # pragma: no cover
        raise ScenarioError("legacy oracle lacks _month_invoices") from exc


def prepare_scenario(
    scenario: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, float], str]:
    transformed = deepcopy(scenario)
    input_data = transformed.get("input")
    if not isinstance(input_data, dict):
        return transformed, {}, "conditional_product"
    method = w_method(input_data)
    shares: dict[str, float] = {}
    for month in input_data.get("miesiace", []) or []:
        if not isinstance(month, dict):
            continue
        evidence = month_evidence(month)
        if evidence is None:
            continue
        month_id = str(month.get("miesiac", ""))
        work = number(evidence.get("godziny_pracy", 0), "godziny_pracy")
        non_ip = number(evidence.get("godziny_nie_IP", 0), "godziny_nie_IP")
        percentage = number(evidence.get("procent_faktury_IP", 100), "procent_faktury_IP")
        try:
            share = calculate_w_share(work, non_ip, percentage, method=method)
        except ValueError as exc:
            raise ScenarioError(f"{month_id}: {exc}") from exc
        shares[month_id] = float(share)
        time_share = (
            Decimal("0")
            if work == 0
            else (Decimal(str(work)) - Decimal(str(non_ip))) / Decimal(str(work))
        )
        compatibility = 100.0 if time_share == 0 else float(share / time_share * 100)
        month["ewidencja"] = {**evidence, "procent_faktury_IP": compatibility}
    policy = input_data.get("polityka_alokacji")
    if (
        isinstance(policy, dict)
        and isinstance(policy.get("koszty_MIX"), dict)
        and policy["koszty_MIX"].get("metoda") == "przychodowa_w_dacie_kosztu"
    ):
        prepare_cost_date_policy(input_data, shares)
    return transformed, shares, method


def prepare_cost_date_policy(input_data: dict[str, Any], shares: dict[str, float]) -> None:
    policy = input_data["polityka_alokacji"]
    revenue_policy = policy["przychody"]
    mix_policy = policy["koszty_MIX"]
    clients = {
        str(client.get("nazwa")): bool(client.get("klauzula_IP", False))
        for client in input_data.get("kontrahenci", [])
        if isinstance(client, dict) and client.get("nazwa")
    }
    for month in input_data.get("miesiace", []) or []:
        if not isinstance(month, dict):
            continue
        month_id = str(month.get("miesiac", ""))
        total = Decimal("0")
        ip = Decimal("0")
        for invoice in month_invoices(month):
            amount = money(invoice_amount(invoice))
            total += amount
            client = str(invoice.get("kontrahent", "default"))
            if not bool(invoice.get("kwalifikuje_IP", clients.get(client, False))):
                continue
            method = str(revenue_policy.get("metoda"))
            key = (
                shares.get(month_id, 0.0) if method == "czasowa_W" else revenue_policy.get("klucz")
            )
            split = (
                float(money(invoice.get("kwota_IP", amount))) if method == "dokumentowa" else None
            )
            allocation = allocate_revenue_monthly(
                float(amount), method, revenue_key=key, document_split_ip=split
            )
            ip += money(allocation["ip_revenue"])
        costs = month.get("koszty", []) or []
        if total <= 0 and costs:
            raise ScenarioError(
                f"{month_id}: revenue-at-cost-date MIX requires positive monthly revenue"
            )
        month_key = float(ip / total) if total else 0.0
        for cost in costs:
            if not isinstance(cost, dict):
                continue
            explicit = str(cost.get("koszyk", cost.get("kategoria", ""))).upper()
            if explicit in {"IP", "NON", "NIE", "WYKLUCZONE", "EXCLUDED"}:
                continue
            cost["allocation_key"] = month_key
            cost["allocation_method"] = "przychodowa_w_dacie_kosztu"
            cost.setdefault("allocation_source", str(mix_policy.get("źródło", "użytkownik")))
    mix_policy["metoda"] = "custom"
    mix_policy["klucz"] = 0.0
    mix_policy.setdefault(
        "uzasadnienie",
        "Każdy koszt MIX dzielony proporcją przychodów istniejącą w miesiącu kosztu.",
    )


def legacy_safe_copy(transformed: dict[str, Any], *, for_validation: bool) -> dict[str, Any]:
    result = deepcopy(transformed)
    input_data = result.get("input")
    if not isinstance(input_data, dict):
        return result
    reliefs = input_data.get("ulgi")
    if isinstance(reliefs, dict):
        reliefs["ikze"] = 0
        reliefs["IKZE"] = 0
        reliefs.pop("termomodernizacja_loty", None)
        if not for_validation:
            reliefs["ulga_BR_IP"] = 0
            reliefs["ulga_BR_NIE"] = 0
    social = input_data.get("zus")
    if isinstance(social, dict):
        health = social.get(
            "odliczenie_zdrowotne_od_dochodu",
            social.get("odliczenie_zdrowotne_PIT", 0),
        )
        social["odliczenie_zdrowotne_PIT"] = health if for_validation else 0
    return result
