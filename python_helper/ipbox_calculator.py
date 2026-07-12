"""
ipbox_calculator.py — Helper module for the IP Box algorithm (v1.0)

Usage: Load this file into an AI agent with Code Interpreter (Claude, ChatGPT Custom GPT).
The agent should use these functions instead of "mental math" for all calculations.

Zero-tolerance math policy: every calculation -> function -> transparent substitution -> result.

License: MIT
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

# ============================================================================
# W Coefficient (Phase 2)
# ============================================================================

def calculate_w_coefficient(
    work_hours: float,
    non_ip_hours: float,
    invoice_percentage: float = 100.0,
) -> dict[str, float | str]:
    """
    Calculate the W coefficient for one month.

    KEY: divisor = actual work hours (excluding vacation and sick leave),
    NOT 160h calendar hours.

    W = ((work_hours - non_ip_hours) * invoice_percentage/100) / work_hours * 100
    """
    if work_hours <= 0:
        return {
            "status": "ERROR",
            "message": "Work hours = 0 (vacation/sick leave all month) — skip month in IP Box",
            "W": 0.0,
        }

    if non_ip_hours > work_hours:
        return {
            "status": "ERROR",
            "message": f"Non-IP hours ({non_ip_hours}h) > Work hours ({work_hours}h) — check data",
            "W": -1,
        }

    effective_ip_hours = (work_hours - non_ip_hours) * (invoice_percentage / 100)
    w_coef = (effective_ip_hours / work_hours) * 100

    # Validation
    if w_coef < 0 or w_coef > 100:
        status = "ERROR"
    elif w_coef == 0:
        status = "SKIP MONTH (W=0)"
    elif w_coef < 50:
        status = "REVIEW_02 (W < 50% — is it too restrictive?)"
    elif w_coef > 95:
        status = "REVIEW_01 (W > 95% — requires strong documentation)"
    else:
        status = "OK"

    formula_str = (
        "W = ((work_hours - non_ip_hours) * invoice_percentage/100) / "
        "work_hours * 100"
    )
    sub_str = (
        f"W = (({work_hours} - {non_ip_hours}) * {invoice_percentage}/100) / "
        f"{work_hours} * 100"
    )
    return {
        "formula": formula_str,
        "substitution": sub_str,
        "effective_ip_hours": round(effective_ip_hours, 2),
        "W": round(w_coef, 2),
        "status": status,
    }


def aggregate_w_multiproject(projects: list[dict]) -> float:
    """
    Aggregate W for multiple projects in one month — revenue-weighted average.

    projects = [{"revenue": 10000, "W": 75}, {"revenue": 5000, "W": 90}, ...]
    """
    total_revenue = sum(p["revenue"] for p in projects)
    if total_revenue == 0:
        return 0.0
    weighted = sum(p["revenue"] * p["W"] for p in projects) / total_revenue
    return round(weighted, 2)


# ============================================================================
# Currencies and exchange rate differences (Phase 4.2, 4.3)
# ============================================================================

def get_nbp_rate(currency: str, date_str: str) -> float | None:
    """
    Get the average NBP rate from table A for a given currency and date (YYYY-MM-DD).
    If date = weekend/holiday -> goes back to the previous business day.
    """
    try:
        import requests
    except ImportError:
        print("⚠️  'requests' library unavailable. Download rate manually from nbp.pl")
        return None

    url = f"http://api.nbp.pl/api/exchangerates/rates/a/{currency.lower()}/{date_str}/?format=json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()["rates"][0]["mid"]
        elif response.status_code == 404:
            # Weekend/holiday — go back one day
            prev_date = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)
            prev = prev_date.strftime("%Y-%m-%d")
            return get_nbp_rate(currency, prev)
        else:
            return None
    except Exception as e:
        print(f"⚠️  NBP API Error: {e}")
        return None


def convert_fx_invoice(
    amount_currency: float,
    currency: str,
    issue_date: str,
    payment_date: str | None = None,
    method: str = "accrual", # "accrual" or "cash"
) -> dict[str, Any]:
    """
    Convert FX invoice to PLN + calculate exchange rate difference.

    IMPORTANT: exchange rate difference ALWAYS goes to NON-IP revenue/costs.
    """
    # Base date for exchange rate
    if method == "accrual":
        base_date = issue_date
    else:  # cash
        if not payment_date:
            return {"error": "Cash method requires payment date"}
        base_date = payment_date

    # Previous business day
    prev_business_date = datetime.strptime(base_date, "%Y-%m-%d") - timedelta(days=1)
    rate_date = prev_business_date.strftime("%Y-%m-%d")

    base_rate = get_nbp_rate(currency, rate_date)
    if base_rate is None:
        return {"error": f"Cannot get NBP rate for {currency} {rate_date} — provide manually"}

    revenue_pln = round(amount_currency * base_rate, 2)

    # Exchange rate difference (if accrual method and we know payment date)
    difference = 0.0
    payment_rate = None
    if method == "accrual" and payment_date and payment_date != base_date:
        payment_prev_date = datetime.strptime(payment_date, "%Y-%m-%d") - timedelta(days=1)
        payment_rate_date = payment_prev_date.strftime("%Y-%m-%d")
        payment_rate = get_nbp_rate(currency, payment_rate_date)
        if payment_rate is not None:
            difference = round((payment_rate - base_rate) * amount_currency, 2)

    return {
        "base_revenue_pln": revenue_pln,
        "base_rate": base_rate,
        "base_rate_date": rate_date,
        "payment_rate": payment_rate,
        "exchange_rate_difference": difference,  # + = non-IP revenue, - = non-IP cost
        "revenue_month": base_date[:7],
        "difference_month": payment_date[:7] if payment_date else None,
        "info": "Exchange rate difference → ALWAYS to NON-IP (never to IP Box!)",
    }


# ============================================================================
# Cost Classification (Phase 3)
# ============================================================================

@dataclass
class CostItem:
    description: str
    amount: float
    basket: str = ""  # IP | MIX | NON | EXCLUDED
    note: str = ""
    allocation_method: str = ""  # dokumentowa | czasowa_W | produktowa | z_interpretacji | custom
    allocation_key: float | None = None  # explicit key 0-1 (None = deferred for annual policy)
    allocation_source: str = ""  # where the allocation policy came from
    nexus_source: str = ""  # own_br | unrelated_br_contractor ... (see nexus_classify)
    nexus_basket: str = ""  # A | B | C | D | poza_nexus
    nexus_amount: float | None = None  # explicit amount for NEXUS (None = use item.amount)

    def __post_init__(self) -> None:
        if self.nexus_amount is not None:
            if not (0 <= self.nexus_amount <= self.amount):
                raise ValueError(
                    f"nexus_amount ({self.nexus_amount}) must be between 0 and cost amount ({self.amount}) for {self.description!r}"
                )


# ============================================================================
# Allocation Policy (Phase 4 — MIX allocation policy)
# ============================================================================

VALID_MIX_METHODS = {"przychodowa_roczna", "czasowa_W", "metraż", "licencje", "projekt", "custom"}
VALID_REVENUE_METHODS = {"dokumentowa", "czasowa_W", "produktowa", "z_interpretacji", "custom"}
VALID_SOURCE = {
    "interpretacja_KIS", "księgowa", "poprzednie_rozliczenie",
    "domyślna_wizard", "użytkownik",
}


@dataclass(frozen=True, kw_only=True)
class AllocationPolicy:
    """
    Allocation policy for MIX costs — how to split costs between IP and non-IP.

    Fields:
        policy_id: Unique identifier for this policy
        revenue_method: How revenue is attributed
        mix_method: How MIX costs are allocated to IP
        mix_key: The percentage key (0.0-1.0) used for mix_method=czasowa_W or custom
        source: Origin of the policy
        justification: Documentation or reasoning for this policy
    """
    policy_id: str
    revenue_method: str = "dokumentowa"
    mix_method: str = "przychodowa_roczna"
    mix_key: float | None = None
    source: str = ""
    justification: str = ""

    def __post_init__(self) -> None:
        """Validate policy fields."""
        aliases = {
            "przychodowy_roczny": "przychodowa_roczna",
            "przychodowy": "przychodowa_roczna",
            "czasowy_W": "czasowa_W",
            "czasowa": "czasowa_W",
        }
        if self.mix_method in aliases:
            object.__setattr__(self, "mix_method", aliases[self.mix_method])

        errors: list[str] = []

        # source is required
        if not self.source:
            errors.append("source is required — must be one of " + str(sorted(VALID_SOURCE)))
        if self.source and self.source not in VALID_SOURCE:
            errors.append(f"source={self.source!r} — must be one of {sorted(VALID_SOURCE)}")

        # valid enums
        if self.mix_method not in VALID_MIX_METHODS:
            errors.append(
                f"mix_method={self.mix_method!r} — must be one of "
                f"{sorted(VALID_MIX_METHODS)}"
            )
        if self.revenue_method not in VALID_REVENUE_METHODS:
            errors.append(
                f"revenue_method={self.revenue_method!r} — must be one of "
                f"{sorted(VALID_REVENUE_METHODS)}"
            )

        # mix_key range 0-1 (only if not None)
        if self.mix_key is not None and not (0 <= self.mix_key <= 1):
            errors.append(f"mix_key must be between 0 and 1, got {self.mix_key}")

        # czasowa_W requires justification + mix_key
        if self.mix_method == "czasowa_W":
            if not self.justification:
                errors.append("czasowa_W requires justification (e.g., time tracking summary)")
            if self.mix_key is None:
                errors.append("czasowa_W requires mix_key")

        # przychodowa_roczna deferred — must NOT have mix_key in monthly policy
        if self.mix_method == "przychodowa_roczna" and self.mix_key is not None:
            errors.append("przychodowa_roczna is deferred; do not set mix_key in monthly policy")

        # custom, metraż, licencje, projekt require justification
        is_justified_method = self.mix_method in {
            "custom", "metraż", "licencje", "projekt",
        }
        if is_justified_method and not self.justification:
            errors.append(f"{self.mix_method} requires justification")

        if errors:
            raise ValueError(
                "AllocationPolicy validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )


# Keywords for automatic classification (Polish terms as per logic)
KEYWORDS_NON = [
    "kawa", "herbata", "cukier", "mleko", "spożyw", "obiad",
    "chemia", "czysto", "płyn", "mydło", "ręcznik",
    "odzież", "ubranie", "buty", "koszula", "bluza",
    "dekoracj", "kwiat", "roślin", "obraz",
    "medicover", "luxmed", "fryzjer", "kosmety",
]

KEYWORDS_EXCLUDED = [
    "kara", "grzywna", "odset.*karn", "sankcj", "mandat",
]

KEYWORDS_SOCIAL_SECURITY = r"(zus.*społeczn|składk.*społeczn|ubezpiecz.*społeczn)"
KEYWORDS_HEALTH_INSURANCE = r"(zdrowotn|nfz)"


def classify_cost(
    item: CostItem,
    social_security_in_kpir: bool,
    health_insurance_in_kpir: bool,
    asset_threshold: float = 10_000,
) -> CostItem:
    """
    Classify a KPiR item into one of the baskets: IP | MIX | NON | EXCLUDED.
    """
    desc = item.description.lower()

    # Guard 1: Social Security
    if re.search(KEYWORDS_SOCIAL_SECURITY, desc):
        if social_security_in_kpir:
            item.basket = "MIX"
            item.note = "ZUS społeczne — in KPiR as cost, DO NOT deduct in PIT"
        else:
            item.basket = "EXCLUDED"
            item.note = "ZUS społeczne — deduction in PIT (not business cost)"
        return item

    # Guard 2: Health Insurance
    if re.search(KEYWORDS_HEALTH_INSURANCE, desc):
        if health_insurance_in_kpir:
            item.basket = "MIX"
            item.note = "Składka zdrowotna — in KPiR (linear, up to limit)"
        else:
            item.basket = "EXCLUDED"
            item.note = "Składka zdrowotna — not in costs (non-deductible in PIT since 2022)"
        return item

    # Guard 3: Fines, penalties
    for pattern in KEYWORDS_EXCLUDED:
        if re.search(pattern, desc):
            item.basket = "EXCLUDED"
            item.note = "Art. 23 ust. 1 pkt 3 PIT — fines/penalties are not costs"
            return item

    # Guard 4: Fixed assets > 10k
    if item.amount > asset_threshold:
        item.basket = "?"
        item.note = (
            f"Item > {asset_threshold:,.0f} PLN — "
            "fixed asset? depreciation or one-time? (ask user)"
        )
        return item

    # Guard 5: NON basket (private)
    for keyword in KEYWORDS_NON:
        if keyword in desc:
            item.basket = "NON"
            item.note = f"Private cost (category: {keyword})"
            return item

    # Default: MIX (common for entire business)
    item.basket = "MIX"
    return item


def allocate_costs_monthly(
    items: list[CostItem],
    *,
    allocation_policy: AllocationPolicy,
    w_coefficient: float | None = None,
    ip_direct_costs: list[CostItem] | None = None,
) -> dict[str, Any]:
    """
    Allocate monthly costs to IP / NON in the correct order using an AllocationPolicy.

    Per-item MIX loop: each MIX cost uses resolve_mix_key().
    For przychodowa_roczna: costs with no allocatable key are deferred to mix_deferred.
    For other methods: resolve_mix_key() must succeed or ValueError is raised.

    Returns:
        costs_ip, costs_non, ip_direct, non_direct, mix, excluded,
        mix_method, mix_key_used, mix_key_source, result_status, mix_deferred
    """
    if w_coefficient is not None:
        if not (0 <= w_coefficient <= 100):
            raise ValueError(f"w_coefficient ({w_coefficient}) must be between 0 and 100")

    ip_direct_costs = ip_direct_costs or []

    sum_ip_direct = sum(i.amount for i in ip_direct_costs)
    sum_ip_from_classification = sum(i.amount for i in items if i.basket == "IP")
    total_ip_direct = sum_ip_direct + sum_ip_from_classification

    sum_non_direct = sum(i.amount for i in items if i.basket == "NON")
    mix_items = [i for i in items if i.basket == "MIX"]
    sum_excluded = sum(i.amount for i in items if i.basket == "EXCLUDED")

    # Per-item MIX allocation loop
    costs_ip = total_ip_direct
    costs_non = sum_non_direct
    mix_deferred: float = 0.0
    mix_ip: float = 0.0
    mix_total_allocated: float = 0.0

    for item in mix_items:
        if allocation_policy.mix_method == "przychodowa_roczna":
            # Per-item allocation_key can allocate immediately; None → deferred
            if item.allocation_key is None:
                mix_deferred += item.amount
                continue
            if not (0 <= item.allocation_key <= 1):
                raise ValueError(
                    f"allocation_key={item.allocation_key} for {item.description!r} "
                    "must be between 0 and 1"
                )
            key = item.allocation_key
        else:
            # Monthly methods require a key — will raise if none found
            key = resolve_mix_key(item, allocation_policy)

        costs_ip += item.amount * key
        costs_non += item.amount * (1 - key)
        mix_ip += item.amount * key
        mix_total_allocated += item.amount

    result_status = "PROVISIONAL" if mix_deferred > 0 else "FINAL"

    sum_mix = sum(i.amount for i in mix_items)

    return {
        "ip_direct": round(total_ip_direct, 2),
        "non_direct": round(sum_non_direct, 2),
        "mix": round(sum_mix, 2),
        "excluded": round(sum_excluded, 2),
        "costs_ip": round(costs_ip, 2),
        "costs_non": round(costs_non, 2),
        "mix_method": allocation_policy.mix_method,
        "mix_key_used": allocation_policy.mix_key,
        "mix_effective_key": (
            round(mix_ip / mix_total_allocated, 6)
            if mix_total_allocated > 0
            else None
        ),
        "mix_key_source": allocation_policy.source,
        "result_status": result_status,
        "mix_deferred": round(mix_deferred, 2),
        "w_coefficient": w_coefficient,
    }


# ============================================================================
# NEXUS (Phase 7.3)
# ============================================================================

def calculate_nexus(A: float, B: float = 0, C: float = 0, D: float = 0) -> dict[str, float]:  # noqa: N803
    """
    Calculate the annual NEXUS (art. 30ca ust. 7 PIT).
    """
    denominator = A + B + C + D
    if denominator == 0:
        return {
            "nexus": 0,
            "message": (
                "A=B=C=D=0 — no qualified costs. "
                "REVIEW_03 (A=0 with IP income? consider minimal costs)."
            ),
        }

    nexus_val = min(1.0, (A * 1.3 + B) / denominator)
    return {
        "A": A,
        "B": B,
        "C": C,
        "D": D,
        "denominator": denominator,
        "formula": "NEXUS = min(1.0, (A*1.3 + B) / (A+B+C+D))",
        "nexus": round(nexus_val, 4),
    }


# ============================================================================
# Tax Cascade (Phase 7.4)
# ============================================================================

def tax_cascade(
    non_ip_income: float,
    ip_income: float,
    nexus: float,
    tax_form: str,  # "linear_19%" | "scale"
    *,
    previous_losses: float = 0,
    social_security_deduction: float = 0,
    ikze: float = 0,
    donations: float = 0,
    internet_tax_relief: float = 0,
    rehabilitative_relief_income: float = 0,
    rd_relief: float = 0,
    thermomodernization_pool: float = 0,
    child_tax_credit: float = 0,
    extra_income_scale: float = 0,
) -> dict[str, Any]:
    """
    Full tax cascade in the binding order.
    """
    valid_tax_forms = frozenset({"linear_19%", "scale"})
    if tax_form not in valid_tax_forms:
        raise ValueError(f"Invalid tax_form: {tax_form!r}. Must be one of {sorted(valid_tax_forms)}")

    steps = []
    remaining = non_ip_income

    # Step 2: Losses
    if previous_losses > 0:
        deduction = min(previous_losses, remaining)
        steps.append({
            "step": "Losses from previous years",
            "deduction": deduction,
            "after": remaining - deduction,
        })
        remaining -= deduction

    # Step 3: Social Security
    if social_security_deduction > 0:
        deduction = min(social_security_deduction, remaining)
        steps.append({
            "step": "Social Security",
            "deduction": deduction,
            "after": remaining - deduction,
        })
        remaining -= deduction

    # Step 4: Use-it-or-lose-it
    for name, amount in [
        ("IKZE", ikze),
        ("Donations", donations),
        ("Internet Relief", internet_tax_relief),
        ("Rehabilitative Relief", rehabilitative_relief_income),
        ("R&D Relief", rd_relief),
    ]:
        if amount > 0:
            deduction = min(amount, remaining)
            steps.append({"step": name, "deduction": deduction, "after": remaining - deduction})
            remaining -= deduction

    # Step 5: Thermomodernization (LAST)
    thermo_used = 0
    if thermomodernization_pool > 0:
        thermo_used = min(thermomodernization_pool, remaining)
        steps.append({
            "step": "Thermomodernization",
            "deduction": thermo_used,
            "after": remaining - thermo_used,
        })
        remaining -= thermo_used

    thermo_carry_over = thermomodernization_pool - thermo_used

    # Step 6: Non-IP Tax
    non_ip_base_rounded = round(max(0, remaining))

    if tax_form == "linear_19%":
        non_ip_tax_before_relief = round(non_ip_base_rounded * 0.19)
    else:  # scale
        total_scale_base = non_ip_base_rounded + round(extra_income_scale)
        if total_scale_base <= 120_000:
            scale_tax = max(0, round(total_scale_base * 0.12 - 3_600))
        else:
            scale_tax = round(10_800 + (total_scale_base - 120_000) * 0.32)

        if total_scale_base > 0:
            non_ip_tax_before_relief = round(scale_tax * (non_ip_base_rounded / total_scale_base))
        else:
            non_ip_tax_before_relief = 0

    # Step 7: IP Tax
    ip_base_rounded = round(max(0, ip_income * nexus))
    ip_tax = round(ip_base_rounded * 0.05)

    # Step 8: Child Credit
    non_ip_tax_after_relief = max(0, non_ip_tax_before_relief - child_tax_credit)
    used_child_credit = min(child_tax_credit, non_ip_tax_before_relief)

    total_tax = non_ip_tax_after_relief + ip_tax

    return {
        "steps": steps,
        "remaining_non_ip_income": round(remaining, 2),
        "non_ip_base_rounded": non_ip_base_rounded,
        "non_ip_tax_before_relief": non_ip_tax_before_relief,
        "used_child_credit": used_child_credit,
        "non_ip_tax_after_relief": non_ip_tax_after_relief,
        "ip_base_rounded": ip_base_rounded,
        "ip_tax": ip_tax,
        "total_tax": total_tax,
        "thermo_used": round(thermo_used, 2),
        "thermo_carry_over": round(thermo_carry_over, 2),
    }


def calculate_overpayment_or_underpayment(
    total_advances: float,
    total_tax: float,
) -> dict[str, float]:
    """Calculate overpayment (+) or underpayment (-)."""
    result = round(total_advances - total_tax, 2)
    return {
        "total_advances": round(total_advances, 2),
        "total_tax": total_tax,
        "result": result,
        "type": "overpayment" if result >= 0 else "underpayment",
    }


# ============================================================================
# Verification Tests (Phase 8)
# ============================================================================

def verify_kpir_balance(
    ip_revenue_sum: float,
    non_ip_revenue_sum: float,
    net_fx_diff: float,
    kpir_revenue: float,
    ip_costs_sum: float,
    non_ip_costs_sum: float,
    kpir_costs_net: float,
    tolerance: float = 0.10,
) -> dict[str, Any]:
    """
    VERIFY 1: KPiR Balance.
    """
    revenue_diff = abs((ip_revenue_sum + non_ip_revenue_sum - net_fx_diff) - kpir_revenue)
    costs_diff = abs((ip_costs_sum + non_ip_costs_sum) - kpir_costs_net)

    return {
        "test": "VERIFY 1 — KPiR Balance",
        "revenue_diff": round(revenue_diff, 2),
        "costs_diff": round(costs_diff, 2),
        "status": "PASS" if (revenue_diff < tolerance and costs_diff < tolerance) else "FAIL",
    }


def verify_private_costs(
    allocated_costs: dict[str, float],
    non_direct_sum: float,
) -> dict[str, Any]:
    """
    VERIFY 2: No Private Costs in IP.
    Ensures that costs in the NON basket did not leak into IP costs.
    In our allocation logic, this is true by construction, but we verify
    if non_direct costs (NON basket) are properly isolated.
    """
    tolerance = 0.02
    leak_detected = False
    details = []

    # Check 1: If non_direct_sum > tolerance, we have private costs present
    if non_direct_sum > tolerance:
        # Check if any value in allocated_costs with IP-related keys might indicate leakage
        ip_related = {k: v for k, v in allocated_costs.items() if "ip" in k.lower()}
        if ip_related and any(v > tolerance for v in ip_related.values()):
            leak_detected = True
            details.append(
                f"Non-direct costs ({non_direct_sum}) found alongside IP costs {ip_related}"
            )

    if leak_detected:
        return {
            "test": "VERIFY 2 — Private Costs",
            "status": "FAIL",
            "details": "; ".join(details),
        }

    return {
        "test": "VERIFY 2 — Private Costs",
        "status": "PASS",
        "non_direct_sum": round(non_direct_sum, 2),
    }


def verify_no_double_social_security(
    in_kpir: bool,
    pit_deduction: float,
    monthly_costs_sum: float,
) -> dict[str, Any]:
    """
    VERIFY 3: No Double Social Security.
    """
    if in_kpir:
        if pit_deduction != 0:
            return {
                "test": "VERIFY 3",
                "status": "FAIL",
                "error": f"In KPiR, but PIT deduction = {pit_deduction}",
            }
    else:
        if monthly_costs_sum != 0:
            return {
                "test": "VERIFY 3",
                "status": "FAIL",
                "error": f"Deducted in PIT, but in costs = {monthly_costs_sum}",
            }

    return {"test": "VERIFY 3 — No Double Social Security", "status": "PASS"}


def verify_tax_cascade(
    non_ip_base_rounded: float,
    thermo_carry_over: float,
) -> dict[str, Any]:
    """
    VERIFY 4: Base >= 0, carry-over >= 0.
    """
    if non_ip_base_rounded < 0:
        return {
            "test": "VERIFY 4",
            "status": "FAIL",
            "error": f"Non-IP base = {non_ip_base_rounded} < 0",
        }
    if thermo_carry_over < 0:
        return {
            "test": "VERIFY 4",
            "status": "FAIL",
            "error": f"Thermo carry-over = {thermo_carry_over} < 0",
        }
    return {"test": "VERIFY 4 — Tax Cascade", "status": "PASS"}


def verify_ip_tax(
    ip_income: float,
    nexus: float,
    declared_base: int,
    declared_tax: int,
) -> dict[str, Any]:
    """
    VERIFY 5: IP Tax calculation.
    """
    expected_base = round(ip_income * nexus)
    expected_tax = round(expected_base * 0.05)

    if expected_base != declared_base:
        return {
            "test": "VERIFY 5",
            "status": "FAIL",
            "error": f"Expected base {expected_base}, declared {declared_base}",
        }
    if expected_tax != declared_tax:
        return {
            "test": "VERIFY 5",
            "status": "FAIL",
            "error": f"Expected tax {expected_tax}, declared {declared_tax}",
        }

    return {"test": "VERIFY 5 — IP Tax", "status": "PASS"}


def verify_overpayment(
    total_advances: float,
    total_tax: float,
    declared_result: float,
    tolerance: float = 1.0,
) -> dict[str, Any]:
    """
    VERIFY 6: Overpayment verification.
    """
    expected = round(total_advances - total_tax, 2)
    diff = abs(expected - declared_result)

    if diff > tolerance:
        return {
            "test": "VERIFY 6",
            "status": "FAIL",
            "error": f"Expected {expected}, declared {declared_result}",
        }
    return {"test": "VERIFY 6 — Overpayment", "status": "PASS"}


# ============================================================================
# NEXUS Classification & MIX Key Resolution (Phase 4 — Allocation)
# ============================================================================

NEXUS_SOURCE_MAP: dict[str, str] = {
    "own_br": "A",
    "unrelated_br_contractor": "B",
    "related_br_contractor": "C",
    "ip_acquisition": "D",
    "indirect_or_general": "poza_nexus",
    "unknown": "poza_nexus",
}


def nexus_classify(item: CostItem, nexus_source: str = "unknown") -> CostItem:
    """
    Classify a cost item into a NEXUS basket based on its nexus_source.
    Validates source against NEXUS_SOURCE_MAP; invalid sources raise ValueError.
    """
    source = nexus_source or "unknown"

    if source not in NEXUS_SOURCE_MAP:
        raise ValueError(
            f"Invalid nexus_source={source!r}. "
            f"Valid values: {sorted(NEXUS_SOURCE_MAP)}"
        )

    item.nexus_source = source
    item.nexus_basket = NEXUS_SOURCE_MAP[source]

    if source == "unknown":
        item.note += (
            "REVIEW_NEXUS_UNKNOWN: nexus_source unknown; "
            "treated as poza_nexus conservatively"
        )

    return item


def resolve_mix_key(
    item: CostItem,
    default_policy: AllocationPolicy,
) -> float:
    """
    Resolve the effective mix key for a cost item.
    Uses `is not None` so that 0.0 is accepted as a valid key (0% to IP).
    """
    if item.basket != "MIX":
        return 0.0

    if item.allocation_key is not None:
        if not (0 <= item.allocation_key <= 1):
            raise ValueError(
                f"allocation_key={item.allocation_key} for {item.description!r} "
                "must be between 0 and 1"
            )
        return item.allocation_key

    if default_policy.mix_key is not None:
        if not (0 <= default_policy.mix_key <= 1):
            raise ValueError(
                f"policy.mix_key={default_policy.mix_key} "
                "must be between 0 and 1"
            )
        return default_policy.mix_key

    raise ValueError(
        f"Cannot resolve mix_key for {item.description!r}: "
        f"item.allocation_key=None, policy.mix_key=None. "
        "Set per-item allocation_key or provide mix_key in AllocationPolicy."
    )


def aggregate_nexus_costs(items: list[CostItem]) -> dict[str, float]:
    """
    Aggregate cost item amounts by nexus_basket.
    MIX costs can only enter A/B/C/D if they have explicit nexus_amount.
    """
    result: dict[str, float] = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "poza_nexus": 0.0}
    for item in items:
        basket = item.nexus_basket or "poza_nexus"
        if basket not in result:
            raise ValueError(f"Invalid nexus_basket={basket!r}")

        if item.basket == "MIX" and basket in {"A", "B", "C", "D"}:
            if item.nexus_amount is None:
                raise ValueError(
                    f"MIX cost {item.description!r} cannot enter NEXUS {basket} "
                    "with full amount. Set explicit nexus_amount."
                )
            amount = item.nexus_amount
            result["poza_nexus"] += item.amount - item.nexus_amount
        else:
            amount = item.nexus_amount if item.nexus_amount is not None else item.amount
            if item.nexus_amount is not None:
                result["poza_nexus"] += item.amount - item.nexus_amount

        if amount < 0:
            raise ValueError(f"nexus amount cannot be negative for {item.description!r}")

        result[basket] += amount

    total_allocated = sum(result.values())
    total_input = sum(item.amount for item in items)
    if abs(total_allocated - total_input) > 0.02:
        raise ValueError(
            f"Cost sum mismatch: allocated {total_allocated:.2f} != input {total_input:.2f}"
        )

    return result


# ============================================================================
# Revenue Allocation (Phase 4.1)
# ============================================================================


def allocate_revenue_monthly(
    base_revenue: float,
    revenue_method: str,
    revenue_key: float | None = None,
    document_split_ip: float | None = None,
) -> dict[str, Any]:
    """
    Split monthly base revenue into IP and non-IP portions.

    Priority by method:
        dokumentowa   — uses document_split_ip (absolute PLN amount)
        czasowa_W     — uses revenue_key as W-derived fraction (0-1)
        produktowa    — uses revenue_key as product fraction (0-1)
        z_interpretacji — uses revenue_key as KIS-stipulated fraction (0-1)
        custom        — uses revenue_key as custom fraction (0-1)
    """
    # --- Validations ---
    errors: list[str] = []

    if base_revenue < 0:
        errors.append(f"base_revenue ({base_revenue}) must be >= 0")

    if revenue_method not in VALID_REVENUE_METHODS:
        errors.append(
            f"revenue_method={revenue_method!r} — must be one of {sorted(VALID_REVENUE_METHODS)}"
        )

    if revenue_method == "dokumentowa":
        if document_split_ip is None:
            errors.append("document_split_ip is required for dokumentowa method")
        elif not (0 <= document_split_ip <= base_revenue):
            errors.append(
                f"document_split_ip ({document_split_ip}) must be between 0 "
                f"and base_revenue ({base_revenue})"
            )
    else:
        if revenue_key is None:
            errors.append(f"revenue_key is required for {revenue_method} method")
        elif not (0 <= revenue_key <= 1):
            errors.append(f"revenue_key ({revenue_key}) must be between 0 and 1")

    if errors:
        raise ValueError(
            "allocate_revenue_monthly validation failed:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    # --- Allocation ---
    if revenue_method == "dokumentowa":
        ip_revenue = document_split_ip  # type: ignore[assignment]
        non_ip_revenue = base_revenue - ip_revenue
    else:
        ip_revenue = base_revenue * revenue_key  # type: ignore[operator]
        non_ip_revenue = base_revenue * (1 - revenue_key)  # type: ignore[operator]

    return {
        "base_revenue": round(base_revenue, 2),
        "ip_revenue": round(ip_revenue, 2),
        "non_ip_revenue": round(non_ip_revenue, 2),
        "revenue_method": revenue_method,
        "revenue_key_used": revenue_key,
        "document_split_ip_used": document_split_ip,
    }


# ============================================================================
# Annual MIX Allocation by Revenue (Phase 4 — deferred mix settlement)
# ============================================================================


def annual_mix_allocation_revenue(
    deferred_mix_total: float,
    annual_ip_revenue: float,
    annual_total_revenue: float,
) -> dict[str, Any]:
    """
    Allocate deferred MIX costs using annual IP revenue proportion
    (roczna metoda przychodowa).

    When monthly MIX costs cannot be resolved under przychodowa_roczna
    method (no per-item allocation key), they are deferred to year-end.
    This function allocates them at annual settlement:

        mix_key = annual_ip_revenue / annual_total_revenue
        costs_ip_mix = deferred_mix_total * mix_key
        costs_non_mix = deferred_mix_total * (1 - mix_key)
    """
    if annual_total_revenue <= 0:
        raise ValueError(
            f"annual_total_revenue must be > 0, got {annual_total_revenue}"
        )
    if annual_ip_revenue < 0:
        raise ValueError(
            f"annual_ip_revenue must be >= 0, got {annual_ip_revenue}"
        )
    if annual_ip_revenue > annual_total_revenue:
        raise ValueError(
            f"annual_ip_revenue ({annual_ip_revenue}) cannot exceed "
            f"annual_total_revenue ({annual_total_revenue})"
        )
    if deferred_mix_total < 0:
        raise ValueError(
            f"deferred_mix_total must be >= 0, got {deferred_mix_total}"
        )

    if deferred_mix_total == 0:
        return {
            "mix_key_used": 0.0,
            "costs_ip_mix": 0.0,
            "costs_non_mix": 0.0,
            "deferred_mix_total": 0.0,
        }

    mix_key = annual_ip_revenue / annual_total_revenue
    costs_ip_mix = deferred_mix_total * mix_key
    costs_non_mix = deferred_mix_total * (1 - mix_key)

    return {
        "mix_key_used": round(mix_key, 4),
        "costs_ip_mix": round(costs_ip_mix, 2),
        "costs_non_mix": round(costs_non_mix, 2),
        "deferred_mix_total": round(deferred_mix_total, 2),
    }


def allocate_multi_ip(
    total_indirect_costs: float,
    software_ip_revenue: float,
    total_revenue: float,
    ip_revenues: dict[str, float],
) -> dict[str, Any]:
    """
    Two-stage allocation of shared indirect costs across multiple IPs.

    Stage 1 — Software IP share of total indirect costs:
        software_share = total_indirect_costs * software_ip_revenue / total_revenue

    Stage 2 — Split software_share among individual IPs by revenue:
        cost_for_ip = software_share * ip_revenue / sum(ip_revenues)

    Note: Direct costs per IP are NOT processed here — this function
    handles only shared/indirect costs.
    """
    if total_indirect_costs < 0:
        raise ValueError(
            f"total_indirect_costs must be >= 0, got {total_indirect_costs}"
        )
    if total_revenue <= 0:
        raise ValueError(
            f"total_revenue must be > 0, got {total_revenue}"
        )
    if software_ip_revenue < 0:
        raise ValueError(
            f"software_ip_revenue must be >= 0, got {software_ip_revenue}"
        )
    if software_ip_revenue > total_revenue:
        raise ValueError(
            f"software_ip_revenue ({software_ip_revenue}) cannot exceed "
            f"total_revenue ({total_revenue})"
        )
    if not ip_revenues:
        raise ValueError("ip_revenues dict must be non-empty")
    for ip_name, ip_rev in ip_revenues.items():
        if ip_rev < 0:
            raise ValueError(
                f"ip_revenues[{ip_name!r}] must be >= 0, got {ip_rev}"
            )
    total_ip_revenue = sum(ip_revenues.values())
    if total_ip_revenue <= 0:
        raise ValueError(
            f"Sum of ip_revenues values must be > 0, got {total_ip_revenue}"
        )
    if abs(total_ip_revenue - software_ip_revenue) > 0.02:
        raise ValueError(
            f"Sum of ip_revenues ({total_ip_revenue}) does not match "
            f"software_ip_revenue ({software_ip_revenue}) — "
            f"difference exceeds 0.02"
        )

    # Stage 1
    software_share = total_indirect_costs * software_ip_revenue / total_revenue

    # Stage 2
    stage2: dict[str, dict[str, float]] = {}
    for ip_name, ip_rev in ip_revenues.items():
        ip_share = ip_rev / total_ip_revenue
        stage2[ip_name] = {
            "costs": round(software_share * ip_share, 2),
            "share": round(ip_share, 4),
        }

    return {
        "stage1": {
            "software_share": round(software_share, 2),
            "software_ip_revenue": round(software_ip_revenue, 2),
            "total_revenue": round(total_revenue, 2),
        },
        "stage2": stage2,
    }


if __name__ == "__main__":
    print("DEMO OK")
