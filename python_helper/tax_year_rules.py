"""Versioned PIT rules for every year in which Polish IP Box exists.

The module deliberately contains only rules that are year-dependent and have an
identified official source.  It does not infer eligibility.  Values passed to
it must already be supported by evidence (payments, returns and ledgers).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable, Mapping

MONEY = Decimal("0.01")
INTEGER = Decimal("1")
IPBOX_FIRST_YEAR = 2019
IPBOX_LAST_VERIFIED_YEAR = 2026


@dataclass(frozen=True, slots=True)
class TaxYearRules:
    year: int
    ikze_business_limit: Decimal
    health_mode: str
    health_linear_limit: Decimal | None
    simultaneous_br_ipbox: bool
    scale_first_rate: Decimal
    scale_threshold: Decimal
    scale_second_rate: Decimal
    scale_fixed_second_bracket: Decimal
    source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ThermomodernizationLot:
    origin_year: int
    remaining_amount: Decimal
    evidence_ref: str = ""

    def __post_init__(self) -> None:
        if self.origin_year < 2019:
            raise ValueError("thermomodernization origin_year cannot precede 2019")
        if self.remaining_amount < 0:
            raise ValueError(
                "thermomodernization remaining_amount must be non-negative"
            )


# Official-source identifiers are intentionally stable and human-auditable.
# Their descriptions are listed in docs/historical-tax-rules.md.
_RULES: dict[int, TaxYearRules] = {
    2019: TaxYearRules(
        2019,
        Decimal("5718.00"),
        "tax_credit_7_75",
        None,
        False,
        Decimal("0.1775"),
        Decimal("85528"),
        Decimal("0.32"),
        Decimal("15181.22"),
        ("MF_IPBOX_2019", "KNF_IKZE", "MF_SCALE_HISTORY", "MF_HEALTH_HISTORY"),
    ),
    2020: TaxYearRules(
        2020,
        Decimal("6272.40"),
        "tax_credit_7_75",
        None,
        False,
        Decimal("0.17"),
        Decimal("85528"),
        Decimal("0.32"),
        Decimal("14539.76"),
        ("MF_IPBOX_2019", "KNF_IKZE", "MF_SCALE_HISTORY", "MF_HEALTH_HISTORY"),
    ),
    2021: TaxYearRules(
        2021,
        Decimal("9466.20"),
        "tax_credit_7_75",
        None,
        False,
        Decimal("0.17"),
        Decimal("85528"),
        Decimal("0.32"),
        Decimal("14539.76"),
        ("MF_IPBOX_2019", "KNF_IKZE", "MF_SCALE_HISTORY", "MF_HEALTH_HISTORY"),
    ),
    2022: TaxYearRules(
        2022,
        Decimal("10659.60"),
        "linear_income_or_cost",
        Decimal("8700.00"),
        True,
        Decimal("0.12"),
        Decimal("120000"),
        Decimal("0.32"),
        Decimal("10800.00"),
        ("MF_IPBOX_2019", "KNF_IKZE", "MF_SCALE_CURRENT", "MF_HEALTH", "MF_IPBOX_BR"),
    ),
    2023: TaxYearRules(
        2023,
        Decimal("12483.00"),
        "linear_income_or_cost",
        Decimal("10200.00"),
        True,
        Decimal("0.12"),
        Decimal("120000"),
        Decimal("0.32"),
        Decimal("10800.00"),
        ("MF_IPBOX_2019", "KNF_IKZE", "MF_SCALE_CURRENT", "MF_HEALTH", "MF_IPBOX_BR"),
    ),
    2024: TaxYearRules(
        2024,
        Decimal("14083.20"),
        "linear_income_or_cost",
        Decimal("11600.00"),
        True,
        Decimal("0.12"),
        Decimal("120000"),
        Decimal("0.32"),
        Decimal("10800.00"),
        ("MF_IPBOX_2019", "KNF_IKZE", "MF_SCALE_CURRENT", "MF_HEALTH", "MF_IPBOX_BR"),
    ),
    2025: TaxYearRules(
        2025,
        Decimal("15611.40"),
        "linear_income_or_cost",
        Decimal("12900.00"),
        True,
        Decimal("0.12"),
        Decimal("120000"),
        Decimal("0.32"),
        Decimal("10800.00"),
        ("MF_IPBOX_2019", "KNF_IKZE", "MF_SCALE_CURRENT", "MF_HEALTH", "MF_IPBOX_BR"),
    ),
    2026: TaxYearRules(
        2026,
        Decimal("16956.00"),
        "linear_income_or_cost",
        Decimal("14100.00"),
        True,
        Decimal("0.12"),
        Decimal("120000"),
        Decimal("0.32"),
        Decimal("10800.00"),
        ("MF_IPBOX_2019", "KNF_IKZE", "MF_SCALE_CURRENT", "MF_HEALTH", "MF_IPBOX_BR"),
    ),
}


def _decimal(name: str, value: float | int | Decimal) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:  # pragma: no cover - Decimal exposes several input errors
        raise ValueError(f"{name} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _nonnegative(name: str, value: float | int | Decimal) -> Decimal:
    result = _decimal(name, value)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def money(value: float | int | Decimal) -> Decimal:
    return _decimal("money", value).quantize(MONEY, rounding=ROUND_HALF_UP)


def tax_round(value: float | int | Decimal) -> int:
    return int(_decimal("tax", value).quantize(INTEGER, rounding=ROUND_HALF_UP))


def supported_years() -> tuple[int, ...]:
    return tuple(sorted(_RULES))


def get_tax_year_rules(year: int) -> TaxYearRules:
    try:
        normalized = int(year)
    except (TypeError, ValueError) as exc:
        raise ValueError("year must be an integer") from exc
    try:
        return _RULES[normalized]
    except KeyError as exc:
        raise ValueError(
            f"unsupported tax year {normalized}; verified IP Box years are "
            f"{IPBOX_FIRST_YEAR}-{IPBOX_LAST_VERIFIED_YEAR}"
        ) from exc


def _historical_tax_reduction(year: int, base: Decimal) -> Decimal:
    """Return the variable tax-reduction amount for 2019-2021."""
    if year == 2019:
        maximum = Decimal("1420.00")
        middle = Decimal("548.30")
        taper_low = Decimal("871.70")
    elif year in {2020, 2021}:
        maximum = Decimal("1360.00")
        middle = Decimal("525.12")
        taper_low = Decimal("834.88")
    else:
        return Decimal("3600.00")

    if base <= 8000:
        return maximum
    if base <= 13000:
        return maximum - taper_low * (base - Decimal("8000")) / Decimal("5000")
    if base <= 85528:
        return middle
    if base <= 127000:
        return middle - middle * (base - Decimal("85528")) / Decimal("41472")
    return Decimal("0")


def calculate_scale_tax(year: int, rounded_base: int | float | Decimal) -> int:
    """Calculate annual PIT under the scale applicable to ``year``."""
    rules = get_tax_year_rules(year)
    base = _nonnegative("rounded_base", rounded_base).quantize(
        INTEGER, rounding=ROUND_HALF_UP
    )
    if year >= 2022:
        if base <= rules.scale_threshold:
            return max(0, tax_round(base * rules.scale_first_rate - Decimal("3600")))
        return tax_round(
            rules.scale_fixed_second_bracket
            + (base - rules.scale_threshold) * rules.scale_second_rate
        )

    gross = base * rules.scale_first_rate
    if base > rules.scale_threshold:
        gross = (
            rules.scale_fixed_second_bracket
            + (base - rules.scale_threshold) * rules.scale_second_rate
        )
    return max(0, tax_round(gross - _historical_tax_reduction(year, base)))


def validate_year_amounts(
    year: int,
    *,
    ikze: float = 0,
    health_income_deduction: float = 0,
    health_tax_credit: float = 0,
    rd_relief_ip: float = 0,
) -> list[str]:
    """Return fail-closed rule violations instead of silently clipping input."""
    rules = get_tax_year_rules(year)
    violations: list[str] = []
    ikze_value = _nonnegative("ikze", ikze)
    health_income = _nonnegative("health_income_deduction", health_income_deduction)
    health_credit = _nonnegative("health_tax_credit", health_tax_credit)
    rd_ip = _nonnegative("rd_relief_ip", rd_relief_ip)

    if ikze_value > rules.ikze_business_limit:
        violations.append("IKZE_LIMIT_EXCEEDED")
    if rules.health_mode == "tax_credit_7_75":
        if health_income > 0:
            violations.append("HEALTH_MODE_INVALID")
    else:
        if health_credit > 0:
            violations.append("HEALTH_MODE_INVALID")
        assert rules.health_linear_limit is not None
        if health_income > rules.health_linear_limit:
            violations.append("HEALTH_LIMIT_EXCEEDED")
    if rd_ip > 0 and not rules.simultaneous_br_ipbox:
        violations.append("BR_IPBOX_NOT_SIMULTANEOUS")
    return violations


def apply_thermomodernization_lots(
    tax_year: int,
    lots: Iterable[ThermomodernizationLot | Mapping[str, Any]],
    available_income: float | int | Decimal,
) -> dict[str, Any]:
    """Use oldest eligible relief lots first and expose expired amounts.

    An unused amount may be carried for no longer than six years counted from
    the end of the year of the first expenditure.  Therefore a lot from year
    ``Y`` may still be used in ``Y + 6`` and expires for ``Y + 7``.
    """
    get_tax_year_rules(tax_year)
    remaining_income = _nonnegative("available_income", available_income)
    normalized: list[ThermomodernizationLot] = []
    for index, raw in enumerate(lots):
        if isinstance(raw, ThermomodernizationLot):
            lot = raw
        elif isinstance(raw, Mapping):
            try:
                origin_year = int(raw["origin_year"])
                amount = money(raw["remaining_amount"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"thermomodernization_lots[{index}] requires origin_year and remaining_amount"
                ) from exc
            lot = ThermomodernizationLot(
                origin_year=origin_year,
                remaining_amount=amount,
                evidence_ref=str(raw.get("evidence_ref", "")),
            )
        else:
            raise ValueError(f"thermomodernization_lots[{index}] must be a mapping")
        if lot.origin_year > tax_year:
            raise ValueError(
                "thermomodernization lot cannot originate in a future year"
            )
        normalized.append(lot)

    opening_total = sum(
        (money(lot.remaining_amount) for lot in normalized), Decimal("0")
    )
    if opening_total > Decimal("53000"):
        raise ValueError("thermomodernization lots exceed the 53000 PLN taxpayer limit")

    rows: list[dict[str, Any]] = []
    used_total = Decimal("0")
    carry_total = Decimal("0")
    expired_total = Decimal("0")
    for lot in sorted(
        normalized, key=lambda item: (item.origin_year, item.evidence_ref)
    ):
        amount = money(lot.remaining_amount)
        expired = tax_year > lot.origin_year + 6
        if expired:
            used = Decimal("0")
            carry = Decimal("0")
            expired_amount = amount
            expired_total += amount
        else:
            used = min(amount, remaining_income)
            remaining_income -= used
            carry = amount - used
            expired_amount = Decimal("0")
            used_total += used
            carry_total += carry
        rows.append(
            {
                "origin_year": lot.origin_year,
                "evidence_ref": lot.evidence_ref,
                "opening_amount": float(amount),
                "used": float(money(used)),
                "carry_over": float(money(carry)),
                "expired": float(money(expired_amount)),
            }
        )
    return {
        "used": float(money(used_total)),
        "carry_over": float(money(carry_total)),
        "expired": float(money(expired_total)),
        "remaining_income": float(money(remaining_income)),
        "lots": rows,
    }


def reconcile_correction_settlement(
    *,
    advances_paid: float,
    original_tax_due: float,
    corrected_tax_due: float,
    refund_already_disbursed: float = 0,
) -> dict[str, float | str]:
    """Distinguish the corrected annual settlement from cash already refunded."""
    advances = money(_nonnegative("advances_paid", advances_paid))
    original_tax = money(_nonnegative("original_tax_due", original_tax_due))
    corrected_tax = money(_nonnegative("corrected_tax_due", corrected_tax_due))
    disbursed = money(
        _nonnegative("refund_already_disbursed", refund_already_disbursed)
    )
    original_overpayment = max(Decimal("0"), advances - original_tax)
    corrected_overpayment = max(Decimal("0"), advances - corrected_tax)
    cash_delta = corrected_overpayment - disbursed
    if cash_delta > 0:
        action = "additional_refund_due"
    elif cash_delta < 0:
        action = "refund_to_repay_or_offset"
    else:
        action = "settled"
    return {
        "original_overpayment": float(money(original_overpayment)),
        "corrected_overpayment": float(money(corrected_overpayment)),
        "refund_already_disbursed": float(disbursed),
        "cash_adjustment": float(money(abs(cash_delta))),
        "action": action,
    }


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
    internet_tax_relief: float = 0,
    rehabilitative_relief_income: float = 0,
    rd_relief_non_ip: float = 0,
    rd_relief_ip: float = 0,
    rd_relief_limit: float = 0,
    thermomodernization_pool: float = 0,
    thermomodernization_lots: Iterable[ThermomodernizationLot | Mapping[str, Any]]
    | None = None,
    child_tax_credit: float = 0,
    extra_income_scale: float = 0,
) -> dict[str, Any]:
    """Calculate a year-aware PIT/IP cascade for 2019-2026.

    The function refuses invalid year/mode combinations.  It does not clip an
    excessive statutory limit because that would hide a defective return.
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
        raise ValueError(
            "post-2021 health income deduction is available only for linear tax"
        )
    if normalized_form == "linear" and values["extra_income_scale"] > 0:
        raise ValueError(
            "linear business and extra scale income require separate returns"
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
        raise ValueError("unsupported personal relief for linear tax")
    if values["internet_tax_relief"] > Decimal("760"):
        raise ValueError("internet relief exceeds 760 PLN")
    if values["thermomodernization_pool"] > Decimal("53000"):
        raise ValueError("thermomodernization pool exceeds 53000 PLN")
    if values["rd_relief_ip"] + values["rd_relief_non_ip"] > values["rd_relief_limit"]:
        raise ValueError("R&D relief exceeds documented limit")
    if thermomodernization_lots is not None and values["thermomodernization_pool"] > 0:
        raise ValueError(
            "use thermomodernization_pool or thermomodernization_lots, not both"
        )

    business_remaining = values["non_ip_income"]
    steps: list[dict[str, float | str]] = []
    rd_non_used = Decimal("0")
    for label, field in (
        ("Previous non-IP business losses", "previous_non_ip_business_losses"),
        ("Health contribution — income", "health_income_deduction"),
        ("R&D relief — non-IP", "rd_relief_non_ip"),
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
            year, thermomodernization_lots, combined_remaining
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

    non_ip_base = tax_round(combined_remaining)
    if normalized_form == "linear":
        non_ip_tax_before_credits = tax_round(Decimal(non_ip_base) * Decimal("0.19"))
    else:
        non_ip_tax_before_credits = calculate_scale_tax(year, non_ip_base)

    rd_ip_used = min(values["rd_relief_ip"], values["ip_income"])
    ip_income_after_rd = values["ip_income"] - rd_ip_used
    ip_base = tax_round(ip_income_after_rd * nexus_dec)
    ip_tax_before_credits = tax_round(Decimal(ip_base) * Decimal("0.05"))

    child_used = min(values["child_tax_credit"], Decimal(non_ip_tax_before_credits))
    non_ip_after_child = Decimal(non_ip_tax_before_credits) - child_used
    total_before_health = non_ip_after_child + Decimal(ip_tax_before_credits)
    health_credit_used = min(values["health_tax_credit"], total_before_health)
    total_tax = tax_round(total_before_health - health_credit_used)

    return {
        "year": year,
        "rules_source_ids": list(rules.source_ids),
        "deduction_steps": steps,
        "thermomodernization_used": float(money(thermo_used)),
        "thermomodernization_carry_over": float(money(thermo_carry)),
        "thermomodernization_expired": (
            float(thermo_lot_result["expired"])
            if thermo_lot_result is not None
            else 0.0
        ),
        "thermomodernization_lots": (
            thermo_lot_result["lots"] if thermo_lot_result is not None else []
        ),
        "non_ip_base_rounded": non_ip_base,
        "extra_income_scale_included": (
            float(values["extra_income_scale"]) if normalized_form == "scale" else 0.0
        ),
        "non_ip_tax_before_child_relief": non_ip_tax_before_credits,
        "child_tax_credit_used": float(money(child_used)),
        "non_ip_tax_final": tax_round(non_ip_after_child),
        "rd_relief_ip_used": float(money(rd_ip_used)),
        "rd_relief_non_ip_used": float(money(rd_non_used)),
        "rd_relief_carry_over": float(
            money(
                values["rd_relief_ip"]
                - rd_ip_used
                + values["rd_relief_non_ip"]
                - rd_non_used
            )
        ),
        "ip_base_rounded": ip_base,
        "ip_tax": ip_tax_before_credits,
        "health_tax_credit_used": float(money(health_credit_used)),
        "total_tax_before_health_credit": tax_round(total_before_health),
        "total_tax": total_tax,
    }
