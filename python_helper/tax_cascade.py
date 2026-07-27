"""Canonical year-aware tax cascade for IP Box settlements.

The qualified IP income receives the 5% rate. Any part of IP income that is not
covered by the NEXUS ratio remains ordinary business income and is taxed under
the taxpayer's normal business form. This module is intentionally separate from
the year-rule catalogue so the cascade can evolve without duplicating limits.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any

from .tax_year_rules import (
    ThermomodernizationLot,
    _decimal,
    _nonnegative,
    apply_thermomodernization_lots,
    calculate_scale_tax,
    get_tax_year_rules,
    money,
    tax_round,
    validate_year_amounts,
)


def calculate_tax_for_year(
    year: int,
    *,
    non_ip_income: float,
    ip_income: float,
    nexus: float,
    tax_form: str,
    previous_non_ip_business_losses: float = 0,
    social_security_deduction: float = 0,
    health_income_deduction: float = 0,
    health_tax_credit: float = 0,
    ikze: float = 0,
    donations: float = 0,
    donation_limit: float = 0,
    internet_tax_relief: float = 0,
    rehabilitative_relief_income: float = 0,
    rd_relief_non_ip: float = 0,
    rd_relief_ip: float = 0,
    rd_relief_limit: float = 0,
    thermomodernization_pool: float = 0,
    thermomodernization_lots: (Iterable[ThermomodernizationLot | Mapping[str, Any]] | None) = None,
    child_tax_credit: float = 0,
    extra_income_scale: float = 0,
) -> dict[str, Any]:
    """Calculate ordinary and preferential tax without losing NEXUS remainder.

    ``ip_income`` is the income from a qualifying right before applying NEXUS.
    After any allowed IP-side R&D relief, NEXUS splits it into:

    * qualified IP income taxed at 5%, and
    * non-preferential IP income taxed with ordinary business income.

    The function keeps the historical return keys for compatibility and adds an
    explicit audit trail for both parts of the split.
    """
    rules = get_tax_year_rules(year)
    aliases = {
        "liniowy_19%": "linear",
        "linear_19%": "linear",
        "skala": "scale",
        "scale": "scale",
    }
    try:
        normalized_form = aliases[tax_form]
    except KeyError as exc:
        raise ValueError("unsupported tax_form") from exc

    inputs = {
        "non_ip_income": non_ip_income,
        "ip_income": ip_income,
        "previous_non_ip_business_losses": previous_non_ip_business_losses,
        "social_security_deduction": social_security_deduction,
        "health_income_deduction": health_income_deduction,
        "health_tax_credit": health_tax_credit,
        "ikze": ikze,
        "donations": donations,
        "donation_limit": donation_limit,
        "internet_tax_relief": internet_tax_relief,
        "rehabilitative_relief_income": rehabilitative_relief_income,
        "rd_relief_non_ip": rd_relief_non_ip,
        "rd_relief_ip": rd_relief_ip,
        "rd_relief_limit": rd_relief_limit,
        "thermomodernization_pool": thermomodernization_pool,
        "child_tax_credit": child_tax_credit,
        "extra_income_scale": extra_income_scale,
    }
    values = {name: _nonnegative(name, value) for name, value in inputs.items()}
    nexus_dec = _decimal("nexus", nexus)
    if not Decimal("0") <= nexus_dec <= Decimal("1"):
        raise ValueError("nexus must be between 0 and 1")

    violations = validate_year_amounts(
        year,
        ikze=float(values["ikze"]),
        health_income_deduction=float(values["health_income_deduction"]),
        health_tax_credit=float(values["health_tax_credit"]),
        rd_relief_ip=float(values["rd_relief_ip"]),
    )
    if violations:
        raise ValueError("year-rule violation: " + ", ".join(violations))
    if normalized_form == "scale" and values["health_income_deduction"] > 0:
        raise ValueError("post-2021 health income deduction is available only for linear tax")
    if normalized_form == "linear" and values["extra_income_scale"] > 0:
        raise ValueError(
            "extra_income_scale with linear business tax requires a separate "
            "scale-return calculation"
        )
    if normalized_form == "linear" and any(
        values[name] > 0
        for name in (
            "donations",
            "internet_tax_relief",
            "rehabilitative_relief_income",
            "child_tax_credit",
        )
    ):
        raise ValueError("unsupported relief for linear tax")
    if values["donations"] > 0:
        if values["donation_limit"] <= 0:
            raise ValueError("positive donations require a verified donation_limit")
        if values["donations"] > values["donation_limit"]:
            raise ValueError("donations exceed the verified donation_limit")
    if values["internet_tax_relief"] > Decimal("760"):
        raise ValueError("internet_tax_relief cannot exceed 760 PLN")
    if values["thermomodernization_pool"] > rules.thermomodernization_limit:
        raise ValueError(
            f"thermomodernization_pool cannot exceed {rules.thermomodernization_limit} PLN"
        )
    if values["rd_relief_ip"] + values["rd_relief_non_ip"] > values["rd_relief_limit"]:
        raise ValueError("allocated R&D relief exceeds documented rd_relief_limit")
    if thermomodernization_lots is not None and values["thermomodernization_pool"] > 0:
        raise ValueError("use thermomodernization_pool or thermomodernization_lots, not both")
    if thermomodernization_lots is not None:
        thermomodernization_mode = "evidence_lots"
        thermomodernization_evidence_status = "VERIFIED"
    elif values["thermomodernization_pool"] > 0:
        thermomodernization_mode = "legacy_pool"
        thermomodernization_evidence_status = "PROVISIONAL"
    else:
        thermomodernization_mode = "none"
        thermomodernization_evidence_status = "NOT_APPLICABLE"

    rd_ip_used = min(values["rd_relief_ip"], values["ip_income"])
    ip_income_after_rd = values["ip_income"] - rd_ip_used
    qualified_ip_income = ip_income_after_rd * nexus_dec
    ordinary_ip_income = ip_income_after_rd - qualified_ip_income

    ordinary_business_before_deductions = values["non_ip_income"] + ordinary_ip_income
    business_remaining = ordinary_business_before_deductions
    steps: list[dict[str, float | str]] = []
    rd_non_used = Decimal("0")
    for label, field in (
        ("Previous ordinary business losses", "previous_non_ip_business_losses"),
        ("Health contribution — ordinary income", "health_income_deduction"),
        ("R&D relief — ordinary income", "rd_relief_non_ip"),
    ):
        requested = values[field]
        used = min(requested, business_remaining)
        business_remaining -= used
        if field == "rd_relief_non_ip":
            rd_non_used = used
        if used:
            steps.append(
                {
                    "step": label,
                    "deduction": float(used),
                    "after": float(business_remaining),
                }
            )

    combined_remaining = business_remaining
    if normalized_form == "scale":
        combined_remaining += values["extra_income_scale"]
    for label, field in (
        ("Social security", "social_security_deduction"),
        ("IKZE", "ikze"),
        ("Donations", "donations"),
        ("Internet relief", "internet_tax_relief"),
        ("Rehabilitative relief", "rehabilitative_relief_income"),
    ):
        used = min(values[field], combined_remaining)
        combined_remaining -= used
        if used:
            steps.append(
                {
                    "step": label,
                    "deduction": float(used),
                    "after": float(combined_remaining),
                }
            )

    thermo_lot_result: dict[str, Any] | None = None
    if thermomodernization_lots is not None:
        thermo_lot_result = apply_thermomodernization_lots(
            year,
            thermomodernization_lots,
            combined_remaining,
        )
        thermo_used = Decimal(str(thermo_lot_result["used"]))
        thermo_carry = Decimal(str(thermo_lot_result["carry_over"]))
        combined_remaining = Decimal(str(thermo_lot_result["remaining_income"]))
    else:
        thermo_used = min(values["thermomodernization_pool"], combined_remaining)
        combined_remaining -= thermo_used
        thermo_carry = values["thermomodernization_pool"] - thermo_used
    if thermo_used:
        steps.append(
            {
                "step": "Thermomodernization",
                "deduction": float(thermo_used),
                "after": float(combined_remaining),
            }
        )

    ordinary_base = tax_round(combined_remaining)
    if normalized_form == "linear":
        ordinary_tax_before_credits = tax_round(Decimal(ordinary_base) * Decimal("0.19"))
    else:
        ordinary_tax_before_credits = calculate_scale_tax(year, ordinary_base)

    ip_base = tax_round(qualified_ip_income)
    ip_tax_before_credits = tax_round(Decimal(ip_base) * Decimal("0.05"))

    child_used = min(values["child_tax_credit"], Decimal(ordinary_tax_before_credits))
    ordinary_after_child = Decimal(ordinary_tax_before_credits) - child_used
    total_before_health = ordinary_after_child + Decimal(ip_tax_before_credits)
    health_credit_used = min(values["health_tax_credit"], total_before_health)
    total_tax = tax_round(total_before_health - health_credit_used)

    return {
        "year": year,
        "rules_source_ids": list(rules.source_ids),
        "deduction_steps": steps,
        "thermomodernization_used": float(money(thermo_used)),
        "thermomodernization_carry_over": float(money(thermo_carry)),
        "thermomodernization_mode": thermomodernization_mode,
        "thermomodernization_evidence_status": (thermomodernization_evidence_status),
        "thermomodernization_rules_source_id": (rules.thermomodernization_source_id),
        "thermomodernization_limit": float(rules.thermomodernization_limit),
        "thermomodernization_expired": (
            float(thermo_lot_result["expired"]) if thermo_lot_result is not None else 0.0
        ),
        "thermomodernization_lots": (
            thermo_lot_result["lots"] if thermo_lot_result is not None else []
        ),
        "ip_income_after_rd": float(money(ip_income_after_rd)),
        "qualified_ip_income": float(money(qualified_ip_income)),
        "ordinary_ip_income": float(money(ordinary_ip_income)),
        "ordinary_business_income_before_deductions": float(
            money(ordinary_business_before_deductions)
        ),
        "ordinary_base_rounded": ordinary_base,
        # Compatibility alias: this base now includes non-preferential IP income.
        "non_ip_base_rounded": ordinary_base,
        "extra_income_scale_included": (
            float(values["extra_income_scale"]) if normalized_form == "scale" else 0.0
        ),
        "non_ip_tax_before_child_relief": ordinary_tax_before_credits,
        "child_tax_credit_used": float(money(child_used)),
        "non_ip_tax_final": tax_round(ordinary_after_child),
        "rd_relief_ip_used": float(money(rd_ip_used)),
        "rd_relief_non_ip_used": float(money(rd_non_used)),
        "rd_relief_carry_over": float(
            money(values["rd_relief_ip"] - rd_ip_used + values["rd_relief_non_ip"] - rd_non_used)
        ),
        "ip_base_rounded": ip_base,
        "ip_tax": ip_tax_before_credits,
        "health_tax_credit_used": float(money(health_credit_used)),
        "total_tax_before_health_credit": tax_round(total_before_health),
        "total_tax": total_tax,
    }
