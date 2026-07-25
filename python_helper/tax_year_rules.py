"""Versioned PIT rules for every year in which Polish IP Box exists.

The module deliberately contains only rules that are year-dependent and have an
identified official source. It does not infer eligibility. Values passed to it
must already be supported by evidence such as payments, returns and ledgers.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .input_validation import strict_decimal

MONEY = Decimal("0.01")
INTEGER = Decimal("1")
IPBOX_FIRST_YEAR = 2019
IPBOX_LAST_VERIFIED_YEAR = 2026


def strict_year(value: Any, field: str = "year") -> int:
    """Accept only an actual integer year; reject strings, floats and booleans."""
    if type(value) is not int:
        raise ValueError(f"{field} must be an integer")
    return value


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
    thermomodernization_limit: Decimal = Decimal("53000")
    thermomodernization_source_id: str = "MF_THERMOMODERNIZATION"


@dataclass(frozen=True, slots=True)
class ThermomodernizationLot:
    origin_year: int
    remaining_amount: Decimal
    evidence_ref: str = ""

    def __post_init__(self) -> None:
        origin_year = strict_year(self.origin_year, "thermomodernization origin_year")
        object.__setattr__(self, "origin_year", origin_year)
        if origin_year < 2019:
            raise ValueError("thermomodernization origin_year cannot precede 2019")
        amount = money(self.remaining_amount)
        object.__setattr__(self, "remaining_amount", amount)
        if not isinstance(self.evidence_ref, str):
            raise ValueError("thermomodernization evidence_ref must be a string")
        evidence_ref = self.evidence_ref.strip()
        if amount > 0 and not evidence_ref:
            raise ValueError("positive thermomodernization lot requires evidence_ref")
        object.__setattr__(self, "evidence_ref", evidence_ref)


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
    return strict_decimal(value, name)


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
    normalized = strict_year(year)
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
    year = strict_year(year)
    rules = get_tax_year_rules(year)
    base = _nonnegative("rounded_base", rounded_base).quantize(INTEGER, rounding=ROUND_HALF_UP)
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
    the end of the year of the first expenditure. Therefore a lot from year
    ``Y`` may still be used in ``Y + 6`` and expires for ``Y + 7``.
    """
    tax_year = strict_year(tax_year, "tax_year")
    rules = get_tax_year_rules(tax_year)
    remaining_income = _nonnegative("available_income", available_income)
    normalized: list[ThermomodernizationLot] = []
    for index, raw in enumerate(lots):
        if isinstance(raw, ThermomodernizationLot):
            lot = raw
        elif isinstance(raw, Mapping):
            try:
                origin_year = strict_year(
                    raw["origin_year"], f"thermomodernization_lots[{index}].origin_year"
                )
                amount = money(raw["remaining_amount"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"thermomodernization_lots[{index}] requires origin_year and remaining_amount"
                ) from exc
            lot = ThermomodernizationLot(
                origin_year=origin_year,
                remaining_amount=amount,
                evidence_ref=raw.get("evidence_ref", ""),
            )
        else:
            raise ValueError(f"thermomodernization_lots[{index}] must be a mapping")
        if lot.origin_year > tax_year:
            raise ValueError("thermomodernization lot cannot originate in a future year")
        normalized.append(lot)

    opening_total = sum((money(lot.remaining_amount) for lot in normalized), Decimal("0"))
    if opening_total > rules.thermomodernization_limit:
        raise ValueError(
            "thermomodernization lots exceed the "
            f"{rules.thermomodernization_limit} PLN taxpayer limit"
        )

    rows: list[dict[str, Any]] = []
    used_total = Decimal("0")
    carry_total = Decimal("0")
    expired_total = Decimal("0")
    for lot in sorted(normalized, key=lambda item: (item.origin_year, item.evidence_ref)):
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
        "mode": "evidence_lots",
        "evidence_status": "VERIFIED",
        "rules_source_id": rules.thermomodernization_source_id,
        "limit": float(rules.thermomodernization_limit),
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
    disbursed = money(_nonnegative("refund_already_disbursed", refund_already_disbursed))
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


def calculate_tax_for_year(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Delegate to the canonical cascade while preserving the historical import path."""
    from .tax_cascade import calculate_tax_for_year as calculate

    return calculate(*args, **kwargs)
