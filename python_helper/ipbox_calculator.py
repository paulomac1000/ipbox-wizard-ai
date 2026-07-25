"""Deterministic calculations used by the IP Box wizard.

The module intentionally keeps three decisions separate:

* attribution of revenue to qualifying IP and non-IP activity,
* allocation of indirect ``MIX`` costs,
* classification of costs into NEXUS A/B/C/D/outside NEXUS.

It is calculation support, not tax or legal advice.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Any

MONEY_QUANT = Decimal("0.01")
INTEGER_QUANT = Decimal("1")
CANONICAL_BASKETS = {"IP", "MIX", "NON", "WYKLUCZONE"}
BASKET_ALIASES = {"EXCLUDED": "WYKLUCZONE", "NIE": "NON"}
THERMOMODERNIZATION_RELIEF_MAX = 53_000.0
NEXUS_SOURCE_MAP = {
    "own_br": "A",
    "unrelated_br_contractor": "B",
    "related_br_contractor": "C",
    "acquired_ip": "D",
    "outside_nexus": "poza_nexus",
    "indirect_or_general": "poza_nexus",
    "unknown": "poza_nexus",
}


def _finite(name: str, value: float | int | Decimal) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def _nonnegative(name: str, value: float | int | Decimal) -> float:
    number = _finite(name, value)
    if number < 0:
        raise ValueError(f"{name} must be >= 0, got {value!r}")
    return number


def _fraction(name: str, value: float | int | Decimal) -> float:
    number = _finite(name, value)
    if not 0 <= number <= 1:
        raise ValueError(f"{name} must be between 0 and 1, got {value!r}")
    return number


def money(value: float | int | Decimal) -> Decimal:
    """Convert a finite value to PLN cents using half-up rounding."""
    _finite("money", value)
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def tax_round(value: float | int | Decimal) -> int:
    """Round a tax base or tax amount to whole PLN, half up."""
    _finite("value", value)
    return int(Decimal(str(value)).quantize(INTEGER_QUANT, rounding=ROUND_HALF_UP))


def calculate_w_coefficient(
    work_hours: float,
    non_ip_hours: float,
    invoice_percentage: float = 100.0,
) -> dict[str, float | str]:
    """Calculate monthly W from actual worked hours."""
    work_hours = _nonnegative("work_hours", work_hours)
    non_ip_hours = _nonnegative("non_ip_hours", non_ip_hours)
    invoice_percentage = _finite("invoice_percentage", invoice_percentage)
    if not 0 <= invoice_percentage <= 100:
        raise ValueError("invoice_percentage must be between 0 and 100")
    if work_hours == 0:
        return {
            "status": "ERROR",
            "message": "Work hours = 0 — STOP_04 or STOP_08 must be resolved from evidence",
            "W": 0.0,
        }
    if non_ip_hours > work_hours:
        return {
            "status": "ERROR",
            "message": "non_ip_hours exceed work_hours",
            "W": 0.0,
        }

    effective_ip_hours = (work_hours - non_ip_hours) * invoice_percentage / 100
    value = effective_ip_hours / work_hours * 100
    if value == 0:
        status = "SKIP_MONTH"
    elif value < 50:
        status = "REVIEW_02"
    elif value > 95:
        status = "REVIEW_01"
    else:
        status = "OK"
    return {
        "formula": (
            "W = ((work_hours - non_ip_hours) * invoice_percentage / 100) / work_hours * 100"
        ),
        "substitution": (
            f"W = (({work_hours} - {non_ip_hours}) * {invoice_percentage} / 100) "
            f"/ {work_hours} * 100"
        ),
        "effective_ip_hours": round(effective_ip_hours, 2),
        "W": round(value, 2),
        "status": status,
    }


def aggregate_w_multiproject(projects: list[dict[str, float]]) -> float:
    """Return a revenue-weighted W for multiple projects."""
    if not projects:
        raise ValueError("projects cannot be empty")
    weighted = Decimal("0")
    revenue_total = Decimal("0")
    for index, project in enumerate(projects):
        if "revenue" not in project or "W" not in project:
            raise ValueError(f"project[{index}] requires revenue and W")
        revenue = Decimal(str(_nonnegative(f"project[{index}].revenue", project["revenue"])))
        w_value = _finite(f"project[{index}].W", project["W"])
        if not 0 <= w_value <= 100:
            raise ValueError(f"project[{index}].W must be between 0 and 100")
        revenue_total += revenue
        weighted += revenue * Decimal(str(w_value))
    if revenue_total == 0:
        raise ValueError("sum of project revenue must be > 0")
    return round(float(weighted / revenue_total), 2)


def get_nbp_rate_with_date(
    currency: str, date_str: str, max_lookback_days: int = 10
) -> tuple[float, str] | None:
    """Fetch an NBP table-A rate and the actual business date used."""
    if not re.fullmatch(r"[A-Za-z]{3}", currency):
        raise ValueError("currency must be a three-letter ISO code")
    if max_lookback_days < 0:
        raise ValueError("max_lookback_days must be >= 0")
    try:
        current = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("date_str must use YYYY-MM-DD") from exc

    try:
        import requests
    except ImportError:
        return None

    for _ in range(max_lookback_days + 1):
        date_value = current.strftime("%Y-%m-%d")
        url = (
            "https://api.nbp.pl/api/exchangerates/rates/a/"
            f"{currency.lower()}/{date_value}/?format=json"
        )
        try:
            response = requests.get(url, timeout=5)
        except requests.RequestException:
            return None
        if response.status_code == 200:
            try:
                rate = float(response.json()["rates"][0]["mid"])
            except (KeyError, IndexError, TypeError, ValueError):
                return None
            if math.isfinite(rate) and rate > 0:
                return rate, date_value
            return None
        if response.status_code != 404:
            return None
        current -= timedelta(days=1)
    return None


def get_nbp_rate(currency: str, date_str: str, max_lookback_days: int = 10) -> float | None:
    """Compatibility helper returning only the rate value."""
    result = get_nbp_rate_with_date(currency, date_str, max_lookback_days)
    return result[0] if result is not None else None


def convert_fx_invoice(
    amount_currency: float,
    currency: str,
    issue_date: str,
    payment_date: str | None = None,
    method: str = "accrual",
) -> dict[str, Any]:
    """Convert an FX invoice and keep exchange differences outside IP revenue."""
    amount_currency = _nonnegative("amount_currency", amount_currency)
    if method not in {"accrual", "cash"}:
        raise ValueError("method must be 'accrual' or 'cash'")
    if payment_date is None:
        raise ValueError("payment_date is required to calculate exchange differences")
    try:
        issue = datetime.strptime(issue_date, "%Y-%m-%d")
        payment = datetime.strptime(payment_date, "%Y-%m-%d") if payment_date else None
    except ValueError as exc:
        raise ValueError("dates must use YYYY-MM-DD") from exc
    if payment is not None and payment < issue:
        raise ValueError("payment_date cannot be earlier than issue_date")
    base_date = issue if method == "accrual" else payment
    assert base_date is not None
    requested_rate_date = (base_date - timedelta(days=1)).strftime("%Y-%m-%d")
    base_lookup = get_nbp_rate_with_date(currency, requested_rate_date)
    if base_lookup is None:
        return {"error": f"NBP rate unavailable for {currency} near {requested_rate_date}"}
    base_rate, base_rate_date = base_lookup

    payment_rate: float | None = None
    payment_rate_date: str | None = None
    difference = Decimal("0")
    if method == "accrual" and payment is not None and payment != issue:
        requested_payment_rate_date = (payment - timedelta(days=1)).strftime("%Y-%m-%d")
        payment_lookup = get_nbp_rate_with_date(currency, requested_payment_rate_date)
        if payment_lookup is None:
            return {
                "error": (
                    "NBP payment-date rate unavailable for "
                    f"{currency} near {requested_payment_rate_date}"
                )
            }
        payment_rate, payment_rate_date = payment_lookup
        difference = money((payment_rate - base_rate) * amount_currency)

    return {
        "base_revenue_pln": float(money(amount_currency * base_rate)),
        "base_rate": base_rate,
        "base_rate_date": base_rate_date,
        "payment_rate": payment_rate,
        "payment_rate_date": payment_rate_date,
        "exchange_rate_difference": float(difference),
        "revenue_month": base_date.strftime("%Y-%m"),
        "difference_month": payment.strftime("%Y-%m") if payment else None,
        "difference_basket": "NON",
    }


def canonical_basket(value: str) -> str:
    """Normalize domain basket aliases to one canonical vocabulary."""
    normalized = BASKET_ALIASES.get(value.upper(), value.upper())
    if normalized not in CANONICAL_BASKETS:
        raise ValueError(f"unsupported basket {value!r}")
    return normalized


@dataclass(frozen=True, slots=True)
class CostItem:
    description: str
    amount: float
    basket: str = ""
    note: str = ""
    allocation_method: str = ""
    allocation_key: float | None = None
    allocation_source: str = ""
    nexus_source: str = "outside_nexus"
    nexus_basket: str = "poza_nexus"
    nexus_amount: float | None = None

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise ValueError("description cannot be empty")
        amount = _nonnegative("amount", self.amount)
        if self.basket:
            object.__setattr__(self, "basket", canonical_basket(self.basket))
        if self.basket == "IP" and not self.allocation_source.strip():
            raise ValueError("direct IP cost requires allocation_source evidence")
        if self.allocation_key is not None:
            _fraction("allocation_key", self.allocation_key)
        if self.nexus_source not in NEXUS_SOURCE_MAP:
            raise ValueError(f"unsupported nexus_source {self.nexus_source!r}")
        expected_nexus_basket = NEXUS_SOURCE_MAP[self.nexus_source]
        if self.nexus_basket != expected_nexus_basket:
            raise ValueError(
                f"nexus_source={self.nexus_source!r} requires "
                f"nexus_basket={expected_nexus_basket!r}"
            )
        if self.nexus_amount is not None:
            nexus_amount = _nonnegative("nexus_amount", self.nexus_amount)
            if nexus_amount > amount:
                raise ValueError("nexus_amount cannot exceed cost amount")


VALID_MIX_METHODS = {
    "przychodowa_roczna",
    "czasowa_W",
    "metraż",
    "licencje",
    "projekt",
    "custom",
}
VALID_REVENUE_METHODS = {
    "dokumentowa",
    "czasowa_W",
    "produktowa",
    "z_interpretacji",
    "custom",
}
VALID_POLICY_SOURCES = {
    "interpretacja_KIS",
    "księgowa",
    "poprzednie_rozliczenie",
    "domyślna_wizard",
    "użytkownik",
}
MIX_METHOD_ALIASES = {
    "przychodowy_roczny": "przychodowa_roczna",
    "przychodowy": "przychodowa_roczna",
    "czasowy_W": "czasowa_W",
    "czasowa": "czasowa_W",
}


@dataclass(frozen=True, kw_only=True, slots=True)
class AllocationPolicy:
    policy_id: str
    revenue_method: str = "dokumentowa"
    mix_method: str = "przychodowa_roczna"
    mix_key: float | None = None
    source: str = "domyślna_wizard"
    justification: str = ""

    def __post_init__(self) -> None:
        normalized = MIX_METHOD_ALIASES.get(self.mix_method, self.mix_method)
        object.__setattr__(self, "mix_method", normalized)
        errors: list[str] = []
        if not self.policy_id.strip():
            errors.append("policy_id is required")
        if self.revenue_method not in VALID_REVENUE_METHODS:
            errors.append(f"invalid revenue_method={self.revenue_method!r}")
        if normalized not in VALID_MIX_METHODS:
            errors.append(f"invalid mix_method={normalized!r}")
        if self.source not in VALID_POLICY_SOURCES:
            errors.append(f"invalid source={self.source!r}")
        if self.mix_key is not None:
            try:
                _fraction("mix_key", self.mix_key)
            except ValueError as exc:
                errors.append(str(exc))
        if normalized == "przychodowa_roczna" and self.mix_key is not None:
            errors.append("przychodowa_roczna is deferred; monthly mix_key must be None")
        if normalized in {"czasowa_W", "metraż", "licencje", "projekt", "custom"}:
            if self.mix_key is None:
                errors.append(f"{normalized} requires mix_key")
            if not self.justification.strip():
                errors.append(f"{normalized} requires justification")
        if errors:
            raise ValueError("AllocationPolicy validation failed:\n- " + "\n- ".join(errors))


PRIVATE_DESCRIPTION_PATTERNS = (
    r"\bprywatn\w*\b",
    r"\bosobist\w*\b",
    r"\bdo\s+domu\b",
    r"\bkawa\b",
    r"\bobiad\w*\b",
    r"\bfryzjer\w*\b",
    r"\bodzież\w*\b",
    r"\bbuty\b",
    r"\bluxmed\b",
    r"\bmedicover\b",
)
EXCLUDED_PATTERNS = (
    r"\bkara\b",
    r"\bgrzywna\b",
    r"\bodsetk[ia].*karn",
    r"\bsankcj",
    r"\bmandat\b",
)
SOCIAL_SECURITY_PATTERN = r"(zus.*społeczn|składk.*społeczn|ubezpiecz.*społeczn)"
HEALTH_PATTERN = r"(zdrowotn|nfz)"


def has_non_deductible_description_signal(description: str) -> bool:
    """Return a token-aware candidate signal; it is not a KUP decision."""
    normalized = description.casefold()
    private = any(re.search(pattern, normalized) for pattern in PRIVATE_DESCRIPTION_PATTERNS)
    statutory = any(re.search(pattern, normalized) for pattern in EXCLUDED_PATTERNS)
    return private or statutory


DIRECT_IP_KEYWORDS = (
    "jetbrains",
    "visual studio",
    "ide",
    "repozytor",
    "narzędzie programistyczne",
    "testy automatyczne",
)


def classify_cost(
    item: CostItem,
    social_security_in_kpir: bool,
    health_insurance_in_kpir: bool,
    asset_threshold: float = 10_000,
) -> CostItem:
    """Classify a KPiR item conservatively and deterministically."""
    asset_threshold = _nonnegative("asset_threshold", asset_threshold)
    description = item.description.lower()
    if re.search(SOCIAL_SECURITY_PATTERN, description):
        if social_security_in_kpir:
            return replace(item, basket="MIX", note="ZUS in KPiR; do not deduct again")
        return replace(item, basket="WYKLUCZONE", note="ZUS handled outside KPiR")
    if re.search(HEALTH_PATTERN, description):
        if health_insurance_in_kpir:
            return replace(item, basket="MIX", note="Health contribution in KPiR")
        return replace(item, basket="WYKLUCZONE", note="Health contribution handled outside costs")
    if has_non_deductible_description_signal(description):
        return replace(
            item,
            basket="MIX",
            note=(
                "Potential non-deductible expense; description alone is not evidence. "
                "Require explicit KUP=false or verified statutory classification to exclude it"
            ),
        )
    if item.basket:
        return item
    if item.amount > asset_threshold:
        return replace(
            item,
            basket="WYKLUCZONE",
            note=(
                "Potential fixed asset above the one-off threshold; exclude the purchase "
                "from this run and enter only documented depreciation/write-off separately"
            ),
        )
    if any(keyword in description for keyword in DIRECT_IP_KEYWORDS):
        return replace(
            item,
            basket="MIX",
            note="Development tool; direct IP requires documented exclusive use",
        )
    return replace(item, basket="MIX", note="Indirect/common business cost")


def allocate_revenue_monthly(
    base_revenue: float,
    revenue_method: str,
    revenue_key: float | None = None,
    document_split_ip: float | None = None,
) -> dict[str, float | str | None]:
    """Split base revenue according to an explicit revenue policy."""
    base_revenue = _nonnegative("base_revenue", base_revenue)
    if revenue_method not in VALID_REVENUE_METHODS:
        raise ValueError(f"unsupported revenue_method={revenue_method!r}")
    total = money(base_revenue)
    if revenue_method == "dokumentowa":
        if document_split_ip is None:
            raise ValueError("document_split_ip is required for dokumentowa")
        split = money(_nonnegative("document_split_ip", document_split_ip))
        if split > total:
            raise ValueError("document_split_ip cannot exceed base_revenue")
        key = float(split / total) if total else 0.0
    else:
        if revenue_key is None:
            raise ValueError(f"revenue_key is required for {revenue_method}")
        key = _fraction("revenue_key", revenue_key)
        split = money(total * Decimal(str(key)))
    non_ip = total - split
    return {
        "base_revenue": float(total),
        "ip_revenue": float(split),
        "non_ip_revenue": float(non_ip),
        "revenue_method": revenue_method,
        "revenue_key_used": key,
        "document_split_ip_used": document_split_ip,
    }


def _assert_unique_instances(*collections: Iterable[CostItem]) -> None:
    seen: set[int] = set()
    for item in (entry for collection in collections for entry in collection):
        identity = id(item)
        if identity in seen:
            raise ValueError("the same CostItem instance cannot be included twice")
        seen.add(identity)


def resolve_mix_key(item: CostItem, policy: AllocationPolicy) -> tuple[float, str, str]:
    """Resolve an explicit MIX key and its audit metadata."""
    if item.allocation_key is not None:
        return (
            _fraction("item.allocation_key", item.allocation_key),
            item.allocation_method or policy.mix_method,
            item.allocation_source or policy.source,
        )
    if policy.mix_key is not None:
        return policy.mix_key, policy.mix_method, policy.source
    raise ValueError(f"no allocation key for MIX cost {item.description!r}")


def allocate_costs_monthly(
    items: list[CostItem],
    *,
    allocation_policy: AllocationPolicy,
    w_coefficient: float | None = None,
    ip_direct_costs: list[CostItem] | None = None,
) -> dict[str, Any]:
    """Allocate monthly costs and return a per-item audit trace."""
    if w_coefficient is not None:
        w_value = _finite("w_coefficient", w_coefficient)
        if not 0 <= w_value <= 100:
            raise ValueError("w_coefficient must be between 0 and 100")
    extra = ip_direct_costs or []
    _assert_unique_instances(items, extra)
    for item in extra:
        if item.basket and item.basket != "IP":
            raise ValueError("ip_direct_costs may contain only IP or unclassified items")
        if not item.allocation_source.strip():
            raise ValueError("ip_direct_costs require allocation_source evidence")
    extra_ids = {id(item) for item in extra}

    totals = {
        "IP": Decimal("0"),
        "NON": Decimal("0"),
        "MIX": Decimal("0"),
        "WYKLUCZONE": Decimal("0"),
        "MIX_DEFERRED": Decimal("0"),
        "MIX_IP": Decimal("0"),
        "MIX_ALLOCATED": Decimal("0"),
    }
    trace: list[dict[str, Any]] = []

    for item in [*items, *extra]:
        basket = item.basket or ("IP" if id(item) in extra_ids else "")
        basket = canonical_basket(basket)
        amount = money(item.amount)
        ip_amount = Decimal("0")
        non_amount = Decimal("0")
        status = "FINAL"
        method = "direct"
        source = item.allocation_source
        key: float | None = None

        if basket == "IP":
            totals["IP"] += amount
            ip_amount = amount
            key = 1.0
        elif basket == "NON":
            totals["NON"] += amount
            non_amount = amount
            key = 0.0
        elif basket == "WYKLUCZONE":
            totals["WYKLUCZONE"] += amount
            method = "excluded"
            status = "WYKLUCZONE"
        elif basket == "MIX":
            totals["MIX"] += amount
            if allocation_policy.mix_method == "przychodowa_roczna":
                if item.allocation_key is not None or item.allocation_method:
                    raise ValueError(
                        "przychodowa_roczna forbids item allocation_key/allocation_method; "
                        "all MIX costs must be deferred to annual true-up"
                    )
                totals["MIX_DEFERRED"] += amount
                method = allocation_policy.mix_method
                source = item.allocation_source or allocation_policy.source
                status = "DEFERRED"
            else:
                key, method, source = resolve_mix_key(item, allocation_policy)
                ip_amount = money(amount * Decimal(str(key)))
                non_amount = amount - ip_amount
                totals["IP"] += ip_amount
                totals["NON"] += non_amount
                totals["MIX_IP"] += ip_amount
                totals["MIX_ALLOCATED"] += amount

        trace.append(
            {
                "description": item.description,
                "amount": float(amount),
                "basket": basket,
                "allocation_method": method,
                "allocation_source": source,
                "allocation_key": key,
                "ip_amount": float(ip_amount),
                "non_ip_amount": float(non_amount),
                "status": status,
                "nexus_source": item.nexus_source,
                "nexus_basket": item.nexus_basket,
                "nexus_amount": item.nexus_amount,
            }
        )

    effective_key = (
        float(totals["MIX_IP"] / totals["MIX_ALLOCATED"]) if totals["MIX_ALLOCATED"] else None
    )
    return {
        "costs_ip": float(totals["IP"]),
        "costs_non": float(totals["NON"]),
        "mix": float(totals["MIX"]),
        "mix_deferred": float(totals["MIX_DEFERRED"]),
        "excluded": float(totals["WYKLUCZONE"]),
        "mix_method": allocation_policy.mix_method,
        "mix_key_source": allocation_policy.source,
        "mix_effective_key": effective_key,
        "result_status": "PROVISIONAL" if totals["MIX_DEFERRED"] else "FINAL",
        "w_coefficient": w_coefficient,
        "allocation_trace": trace,
    }


def annual_mix_allocation_revenue(
    deferred_mix_total: float,
    annual_ip_revenue: float,
    annual_total_revenue: float,
) -> dict[str, float | str]:
    """Perform the final annual true-up for deferred MIX."""
    deferred_mix_total = _nonnegative("deferred_mix_total", deferred_mix_total)
    annual_ip_revenue = _nonnegative("annual_ip_revenue", annual_ip_revenue)
    annual_total_revenue = _nonnegative("annual_total_revenue", annual_total_revenue)
    if annual_total_revenue == 0:
        raise ValueError("annual_total_revenue must be > 0")
    if annual_ip_revenue > annual_total_revenue:
        raise ValueError("annual_ip_revenue cannot exceed annual_total_revenue")
    key = annual_ip_revenue / annual_total_revenue
    total = money(deferred_mix_total)
    ip_amount = money(total * Decimal(str(key)))
    non_amount = total - ip_amount
    return {
        "method": "przychodowa_roczna",
        "effective_key": key,
        "mix_total": float(total),
        "mix_ip": float(ip_amount),
        "mix_non_ip": float(non_amount),
        "status": "FINAL",
    }


def _split_money_by_weights(total: float, weights: Mapping[str, float]) -> dict[str, float]:
    """Allocate every cent with the largest-remainder method."""
    total_dec = money(total)
    if not weights:
        raise ValueError("weights cannot be empty")
    normalized: dict[str, Decimal] = {}
    for name, value in weights.items():
        normalized[name] = Decimal(str(_nonnegative(f"weights[{name!r}]", value)))
    denominator = sum(normalized.values(), Decimal("0"))
    if denominator == 0:
        if total_dec == 0:
            return {name: 0.0 for name in normalized}
        raise ValueError("sum of weights must be > 0 when total is positive")

    raw = {name: total_dec * value / denominator for name, value in normalized.items()}
    floors = {
        name: int((value * 100).quantize(Decimal("1"), rounding=ROUND_DOWN))
        for name, value in raw.items()
    }
    remaining = int(total_dec * 100) - sum(floors.values())
    order = sorted(
        raw,
        key=lambda name: ((raw[name] * 100) - floors[name], name),
        reverse=True,
    )
    for name in order[:remaining]:
        floors[name] += 1
    return {name: float(Decimal(cents) / 100) for name, cents in floors.items()}


def allocate_multi_ip(
    total_indirect_costs: float,
    software_ip_revenue: float,
    total_revenue: float,
    ip_revenues: Mapping[str, float],
) -> dict[str, Any]:
    """Allocate indirect costs in two stages while preserving cents."""
    total_indirect_costs = _nonnegative("total_indirect_costs", total_indirect_costs)
    software_ip_revenue = _nonnegative("software_ip_revenue", software_ip_revenue)
    total_revenue = _nonnegative("total_revenue", total_revenue)
    if total_revenue == 0:
        raise ValueError("total_revenue must be > 0")
    if software_ip_revenue == 0:
        raise ValueError("software_ip_revenue must be > 0")
    if software_ip_revenue > total_revenue:
        raise ValueError("software_ip_revenue cannot exceed total_revenue")
    if not ip_revenues:
        raise ValueError("ip_revenues cannot be empty")
    total_ip_revenue = sum(
        _nonnegative(f"ip_revenues[{name!r}]", value) for name, value in ip_revenues.items()
    )
    if money(total_ip_revenue) != money(software_ip_revenue):
        raise ValueError("sum(ip_revenues) must equal software_ip_revenue at PLN-cent precision")

    stage1 = money(
        Decimal(str(total_indirect_costs))
        * Decimal(str(software_ip_revenue))
        / Decimal(str(total_revenue))
    )
    allocations = _split_money_by_weights(float(stage1), ip_revenues)
    return {
        "stage1_software_share": float(stage1),
        "stage1_non_software_share": float(money(total_indirect_costs) - stage1),
        "projects": allocations,
    }


def nexus_classify(item: CostItem, source: str) -> CostItem:
    """Attach a validated NEXUS source and basket."""
    if source not in NEXUS_SOURCE_MAP:
        raise ValueError(f"unsupported nexus source {source!r}")
    return replace(item, nexus_source=source, nexus_basket=NEXUS_SOURCE_MAP[source])


def aggregate_nexus_costs(items: list[CostItem]) -> dict[str, float]:
    """Aggregate NEXUS independently from income-allocation baskets."""
    totals = {name: Decimal("0") for name in ("A", "B", "C", "D", "poza_nexus")}
    for item in items:
        basket = item.nexus_basket or NEXUS_SOURCE_MAP.get(item.nexus_source, "poza_nexus")
        if basket not in totals:
            raise ValueError(f"invalid nexus_basket={basket!r}")
        amount = money(item.amount)
        if basket in {"A", "B", "C", "D"}:
            if item.basket == "MIX" and item.nexus_amount is None:
                raise ValueError(f"MIX cost {item.description!r} requires explicit nexus_amount")
            qualified = money(item.nexus_amount if item.nexus_amount is not None else amount)
            if qualified > amount:
                raise ValueError("nexus_amount cannot exceed item amount")
            totals[basket] += qualified
            totals["poza_nexus"] += amount - qualified
        else:
            totals["poza_nexus"] += amount
    input_total = sum((money(item.amount) for item in items), Decimal("0"))
    allocated_total = sum(totals.values(), Decimal("0"))
    if input_total != allocated_total:
        raise ValueError("NEXUS allocation does not preserve total cost")
    return {name: float(value) for name, value in totals.items()}


def calculate_nexus(
    component_a: float,
    component_b: float = 0,
    component_c: float = 0,
    component_d: float = 0,
) -> dict[str, float | str]:
    """Calculate NEXUS; zero qualifying costs always produce zero."""
    values = {
        "A": _nonnegative("A", component_a),
        "B": _nonnegative("B", component_b),
        "C": _nonnegative("C", component_c),
        "D": _nonnegative("D", component_d),
    }
    denominator = sum(values.values())
    if denominator == 0:
        return {
            **values,
            "denominator": 0.0,
            "nexus": 0.0,
            "message": "A=B=C=D=0 — no qualifying NEXUS costs",
        }
    result = min(1.0, ((values["A"] + values["B"]) * 1.3) / denominator)
    return {
        **values,
        "denominator": denominator,
        "formula": "min(1, ((A+B)*1.3)/(A+B+C+D))",
        "nexus": round(result, 6),
    }


def tax_cascade(
    non_ip_income: float,
    ip_income: float,
    nexus: float,
    tax_form: str,
    *,
    year: int,
    previous_non_ip_business_losses: float = 0,
    social_security_deduction: float = 0,
    health_contribution_deduction: float = 0,
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
    child_tax_credit: float = 0,
    extra_income_scale: float = 0,
) -> dict[str, Any]:
    """Compatibility adapter to the single canonical year-aware tax cascade."""
    from .tax_cascade import calculate_tax_for_year

    return calculate_tax_for_year(
        year,
        non_ip_income=non_ip_income,
        ip_income=ip_income,
        nexus=nexus,
        tax_form=tax_form,
        previous_non_ip_business_losses=previous_non_ip_business_losses,
        social_security_deduction=social_security_deduction,
        health_income_deduction=health_contribution_deduction,
        health_tax_credit=health_tax_credit,
        ikze=ikze,
        donations=donations,
        donation_limit=donation_limit,
        internet_tax_relief=internet_tax_relief,
        rehabilitative_relief_income=rehabilitative_relief_income,
        rd_relief_non_ip=rd_relief_non_ip,
        rd_relief_ip=rd_relief_ip,
        rd_relief_limit=rd_relief_limit,
        thermomodernization_pool=thermomodernization_pool,
        child_tax_credit=child_tax_credit,
        extra_income_scale=extra_income_scale,
    )


def calculate_overpayment(
    tax_due: float,
    advances_paid: float,
    previous_year_refund_adjustment: float = 0,
) -> dict[str, float | str]:
    """Return a positive overpayment or positive amount due."""
    tax_due = _nonnegative("tax_due", tax_due)
    advances_paid = _nonnegative("advances_paid", advances_paid)
    adjustment = _nonnegative("previous_year_refund_adjustment", previous_year_refund_adjustment)
    difference = tax_round(advances_paid - adjustment - tax_due)
    if difference > 0:
        return {"type": "overpayment", "amount": difference}
    if difference < 0:
        return {"type": "amount_due", "amount": abs(difference)}
    return {"type": "settled", "amount": 0}


def verify_kpir_balance(
    kpir_revenue: float,
    kpir_costs: float,
    computed_revenue: float,
    computed_costs: float,
    tolerance: float = 1.0,
) -> dict[str, Any]:
    """Verify monthly totals against an external KPiR summary."""
    for name, value in (
        ("kpir_revenue", kpir_revenue),
        ("kpir_costs", kpir_costs),
        ("computed_revenue", computed_revenue),
        ("computed_costs", computed_costs),
        ("tolerance", tolerance),
    ):
        _nonnegative(name, value)
    revenue_diff = abs(money(kpir_revenue) - money(computed_revenue))
    costs_diff = abs(money(kpir_costs) - money(computed_costs))
    passed = revenue_diff <= Decimal(str(tolerance)) and costs_diff <= Decimal(str(tolerance))
    return {
        "test": "TEST_1",
        "status": "PASS" if passed else "FAIL",
        "revenue_difference": float(revenue_diff),
        "cost_difference": float(costs_diff),
    }


def verify_private_costs(private_costs_allocated_to_business: float) -> dict[str, Any]:
    """Fail if a known private amount remains in IP or MIX."""
    amount = _nonnegative(
        "private_costs_allocated_to_business", private_costs_allocated_to_business
    )
    return {
        "test": "TEST_2",
        "status": "PASS" if money(amount) == 0 else "FAIL",
        "private_amount_allocated_to_business": float(money(amount)),
    }


def verify_zus_no_double_dip(
    social_security_in_kpir: bool,
    social_security_deduction: float,
    health_in_kpir: bool,
    health_deduction: float,
) -> dict[str, Any]:
    """Detect social-security or health-contribution double-dipping."""
    social = _nonnegative("social_security_deduction", social_security_deduction)
    health = _nonnegative("health_deduction", health_deduction)
    problems: list[str] = []
    if social_security_in_kpir and social:
        problems.append("social security appears in KPiR and PIT deduction")
    if health_in_kpir and health:
        problems.append("health contribution appears in KPiR and PIT deduction")
    return {
        "test": "TEST_3",
        "status": "FAIL" if problems else "PASS",
        "problems": problems,
    }


def verify_ip_tax(
    ip_income: float,
    nexus: float,
    declared_base: float,
    declared_tax: float,
) -> dict[str, Any]:
    """Verify IP tax with the same rounding policy as the calculator."""
    ip_income = _finite("ip_income", ip_income)
    nexus = _fraction("nexus", nexus)
    declared_base = _nonnegative("declared_base", declared_base)
    declared_tax = _nonnegative("declared_tax", declared_tax)
    expected_base = tax_round(max(0.0, ip_income * nexus))
    expected_tax = tax_round(expected_base * 0.05)
    passed = tax_round(declared_base) == expected_base and tax_round(declared_tax) == expected_tax
    return {
        "test": "TEST_5",
        "status": "PASS" if passed else "FAIL",
        "expected_base": expected_base,
        "expected_tax": expected_tax,
    }


def compare_allocation_methods(
    *,
    mix_total: float,
    annual_ip_revenue: float,
    annual_total_revenue: float,
    annual_w_percent: float,
    ip_income_before_mix: float,
    nexus: float,
) -> dict[str, Any]:
    """Compare methods transparently without choosing by tax outcome."""
    mix_total = _nonnegative("mix_total", mix_total)
    ip_income_before_mix = _nonnegative("ip_income_before_mix", ip_income_before_mix)
    nexus = _fraction("nexus", nexus)
    annual_w_percent = _finite("annual_w_percent", annual_w_percent)
    if not 0 <= annual_w_percent <= 100:
        raise ValueError("annual_w_percent must be between 0 and 100")
    revenue = annual_mix_allocation_revenue(
        mix_total,
        annual_ip_revenue,
        annual_total_revenue,
    )
    rows: list[dict[str, Any]] = []
    for method, key, mix_ip in (
        ("przychodowa_roczna", revenue["effective_key"], revenue["mix_ip"]),
        ("czasowa_W", annual_w_percent / 100, float(money(mix_total * annual_w_percent / 100))),
    ):
        income = max(0.0, ip_income_before_mix - float(mix_ip))
        base = tax_round(income * nexus)
        rows.append(
            {
                "method": method,
                "key": key,
                "mix_ip": mix_ip,
                "ip_income_after_mix": income,
                "ip_tax": tax_round(base * 0.05),
            }
        )
    return {
        "methods": rows,
        "tax_difference": abs(rows[0]["ip_tax"] - rows[1]["ip_tax"]),
        "decision_rule": "follow documented policy/KIS, never the lower-tax result",
    }
