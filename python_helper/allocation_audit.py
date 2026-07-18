"""Auditable allocation methods and guards derived from real-world failure modes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable, Mapping

MONEY = Decimal("0.01")
VALID_W_METHODS = {"conditional_product", "disjoint_components", "time_only"}


@dataclass(frozen=True, slots=True)
class AllocationFinding:
    code: str
    month: str | None
    expected: Decimal | None = None
    actual: Decimal | None = None
    detail: str = ""


def _decimal(name: str, value: float | int | Decimal) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:  # pragma: no cover
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


def calculate_w_share(
    work_hours: float,
    non_ip_hours: float,
    invoice_percentage: float = 100,
    *,
    method: str = "conditional_product",
) -> Decimal:
    """Return an IP share in [0, 1] with explicit field semantics.

    ``conditional_product`` means the invoice percentage is a second filter
    applied to IP-capable work time. ``disjoint_components`` means the invoice
    percentage and non-IP hours describe disjoint parts of the same invoice.
    ``time_only`` ignores the invoice percentage by policy.
    """
    if method not in VALID_W_METHODS:
        raise ValueError(f"unsupported W method {method!r}")
    work = _nonnegative("work_hours", work_hours)
    non_ip = _nonnegative("non_ip_hours", non_ip_hours)
    percentage = _nonnegative("invoice_percentage", invoice_percentage) / Decimal("100")
    if percentage > 1:
        raise ValueError("invoice_percentage must not exceed 100")
    if work == 0:
        raise ValueError("work_hours must be > 0")
    if non_ip > work:
        raise ValueError("non_ip_hours cannot exceed work_hours")
    time_share = (work - non_ip) / work
    if method == "conditional_product":
        share = time_share * percentage
    elif method == "disjoint_components":
        share = percentage - non_ip / work
    else:
        share = time_share
    if not Decimal("0") <= share <= Decimal("1"):
        raise ValueError(
            "W method produced a share outside 0-1; field semantics contradict"
        )
    return share


def calculate_w_percent(*args: Any, **kwargs: Any) -> float:
    return round(float(calculate_w_share(*args, **kwargs) * 100), 2)


def _closest_signature(
    total: Decimal,
    actual: Decimal,
    work: Decimal,
    non_ip: Decimal,
    percentage: Decimal,
    tolerance: Decimal,
) -> str:
    candidates = {
        "invoice_percentage_once": money(total * percentage),
        "invoice_percentage_squared": money(total * percentage * percentage),
        "conditional_product": money(total * ((work - non_ip) / work) * percentage),
        "disjoint_components": money(total * (percentage - non_ip / work)),
        "time_only": money(total * ((work - non_ip) / work)),
        "full_revenue": money(total),
    }
    distances = {name: abs(value - actual) for name, value in candidates.items()}
    name = min(distances, key=distances.get)
    return name if distances[name] <= tolerance else "unclassified"


def audit_revenue_allocation(
    months: Iterable[Mapping[str, Any]],
    *,
    tolerance: float = 0.02,
) -> list[AllocationFinding]:
    """Detect double application, silent method switches and split imbalance."""
    tolerance_dec = money(tolerance)
    findings: list[AllocationFinding] = []
    signatures: list[tuple[str, str]] = []
    for index, record in enumerate(months):
        month = str(record.get("month", record.get("miesiac", index + 1)))
        total = money(_nonnegative("total_revenue", record.get("total_revenue", 0)))
        reported_ip = money(
            _nonnegative("reported_ip_revenue", record.get("reported_ip_revenue", 0))
        )
        reported_non = money(
            _nonnegative(
                "reported_non_ip_revenue",
                record.get("reported_non_ip_revenue", total - reported_ip),
            )
        )
        if reported_ip + reported_non != total:
            findings.append(
                AllocationFinding(
                    "REVENUE_SPLIT_DOES_NOT_BALANCE",
                    month,
                    total,
                    reported_ip + reported_non,
                )
            )
        work = _nonnegative("work_hours", record.get("work_hours", 0))
        non_ip = _nonnegative("non_ip_hours", record.get("non_ip_hours", 0))
        percentage = _nonnegative(
            "invoice_percentage", record.get("invoice_percentage", 100)
        ) / Decimal("100")
        method = str(record.get("w_method", "conditional_product"))
        expected_share = calculate_w_share(
            float(work), float(non_ip), float(percentage * 100), method=method
        )
        expected = money(total * expected_share)
        signature = _closest_signature(
            total,
            reported_ip,
            work,
            non_ip,
            percentage,
            tolerance_dec,
        )
        # A 100% invoice percentage makes ``invoice_percentage_once`` numerically
        # identical to ``full_revenue``.  The semantic guard must prefer the
        # latter whenever declared non-IP evidence still produces W < 100%.
        if abs(reported_ip - total) <= tolerance_dec and expected_share < 1:
            signature = "full_revenue"
        signatures.append((month, signature))
        if abs(expected - reported_ip) > tolerance_dec:
            findings.append(
                AllocationFinding(
                    "REVENUE_ALLOCATION_MISMATCH",
                    month,
                    expected,
                    reported_ip,
                    f"declared W method={method}; observed signature={signature}",
                )
            )
        if signature == "invoice_percentage_squared" and percentage not in {0, 1}:
            findings.append(
                AllocationFinding(
                    "INVOICE_PERCENTAGE_DOUBLE_APPLIED",
                    month,
                    expected,
                    reported_ip,
                )
            )
        if signature == "full_revenue" and expected_share < 1:
            findings.append(
                AllocationFinding(
                    "FULL_REVENUE_DESPITE_NON_IP_SHARE",
                    month,
                    expected,
                    reported_ip,
                )
            )

    meaningful = [
        (month, signature)
        for month, signature in signatures
        if signature != "unclassified"
    ]
    signature_counts = Counter(signature for _, signature in meaningful)
    if len(signature_counts) > 1:
        findings.append(
            AllocationFinding(
                "ALLOCATION_METHOD_SWITCH",
                None,
                detail=", ".join(
                    f"{name}={count}"
                    for name, count in sorted(signature_counts.items())
                ),
            )
        )
    return findings


def reconcile_return_to_ledger(
    ledger: Mapping[str, float],
    tax_return: Mapping[str, float],
    *,
    tolerance: float = 0.01,
) -> list[AllocationFinding]:
    """Reconcile both totals and the IP/NON split; equal grand totals are insufficient."""
    tolerance_dec = money(tolerance)
    keys = ("ip_revenue", "non_ip_revenue", "ip_cost", "non_ip_cost")
    findings: list[AllocationFinding] = []
    for key in keys:
        expected = money(_nonnegative(f"ledger.{key}", ledger.get(key, 0)))
        actual = money(_nonnegative(f"tax_return.{key}", tax_return.get(key, 0)))
        if abs(expected - actual) > tolerance_dec:
            findings.append(
                AllocationFinding(
                    f"RETURN_{key.upper()}_MISMATCH", None, expected, actual
                )
            )
    ledger_revenue = money(
        ledger.get("ip_revenue", 0) + ledger.get("non_ip_revenue", 0)
    )
    return_revenue = money(
        tax_return.get("ip_revenue", 0) + tax_return.get("non_ip_revenue", 0)
    )
    ledger_cost = money(ledger.get("ip_cost", 0) + ledger.get("non_ip_cost", 0))
    return_cost = money(tax_return.get("ip_cost", 0) + tax_return.get("non_ip_cost", 0))
    if abs(ledger_revenue - return_revenue) <= tolerance_dec and any(
        finding.code.endswith("REVENUE_MISMATCH") for finding in findings
    ):
        findings.append(
            AllocationFinding(
                "RETURN_REVENUE_CLASSIFICATION_SHIFT",
                None,
                ledger_revenue,
                return_revenue,
            )
        )
    if abs(ledger_cost - return_cost) <= tolerance_dec and any(
        finding.code.endswith("COST_MISMATCH") for finding in findings
    ):
        findings.append(
            AllocationFinding(
                "RETURN_COST_CLASSIFICATION_SHIFT", None, ledger_cost, return_cost
            )
        )
    if abs(ledger_revenue - return_revenue) > tolerance_dec:
        findings.append(
            AllocationFinding(
                "RETURN_TOTAL_REVENUE_MISMATCH", None, ledger_revenue, return_revenue
            )
        )
    if abs(ledger_cost - return_cost) > tolerance_dec:
        findings.append(
            AllocationFinding(
                "RETURN_TOTAL_COST_MISMATCH", None, ledger_cost, return_cost
            )
        )
    return findings


def allocate_mix_at_cost_date(
    costs: Iterable[Mapping[str, Any]],
    monthly_revenue: Mapping[str, Mapping[str, float]],
) -> dict[str, Any]:
    """Allocate each shared cost using the revenue ratio existing on its cost date/month."""
    rows: list[dict[str, Any]] = []
    ip_total = Decimal("0")
    non_total = Decimal("0")
    for index, raw in enumerate(costs):
        month = str(raw.get("month", raw.get("miesiac", "")))
        if not month or month not in monthly_revenue:
            raise ValueError(f"cost[{index}] has no matching monthly revenue")
        amount = money(
            _nonnegative(
                f"cost[{index}].amount", raw.get("amount", raw.get("kwota", 0))
            )
        )
        revenues = monthly_revenue[month]
        ip_revenue = money(
            _nonnegative(f"monthly_revenue[{month}].ip", revenues.get("ip", 0))
        )
        total_revenue = money(
            _nonnegative(f"monthly_revenue[{month}].total", revenues.get("total", 0))
        )
        if total_revenue <= 0:
            raise ValueError(f"monthly revenue denominator for {month} must be > 0")
        if ip_revenue > total_revenue:
            raise ValueError(f"monthly IP revenue for {month} exceeds total revenue")
        key = ip_revenue / total_revenue
        ip_amount = money(amount * key)
        non_amount = amount - ip_amount
        ip_total += ip_amount
        non_total += non_amount
        rows.append(
            {
                "month": month,
                "amount": float(amount),
                "key": float(key),
                "ip_amount": float(ip_amount),
                "non_ip_amount": float(non_amount),
            }
        )
    return {
        "method": "przychodowa_w_dacie_kosztu",
        "ip_total": float(ip_total),
        "non_ip_total": float(non_total),
        "rows": rows,
    }
