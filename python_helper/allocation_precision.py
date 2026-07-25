"""Precision-aware audit of revenue allocation streams."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .allocation_audit import AllocationFinding, calculate_w_share, money
from .input_validation import strict_decimal

DEFAULT_W_PRECISION_PP = Decimal("0.01")
DEFAULT_INVOICE_PERCENTAGE_PRECISION_PP = Decimal("0.01")


def _decimal(name: str, value: float | int | Decimal) -> Decimal:
    return strict_decimal(value, name)


def _nonnegative(name: str, value: float | int | Decimal) -> Decimal:
    result = _decimal(name, value)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _positive(name: str, value: float | int | Decimal) -> Decimal:
    result = _nonnegative(name, value)
    if result <= 0:
        raise ValueError(f"{name} must be > 0")
    return result


def _first(record: Mapping[str, Any], *names: str) -> Any | None:
    for name in names:
        if name in record and record[name] is not None:
            return record[name]
    return None


def _round_to_quantum(value: Decimal, quantum: Decimal) -> Decimal:
    return (value / quantum).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * quantum


def amount_tolerance(
    total: Decimal,
    *,
    base: Decimal,
    precision_pp: Decimal = Decimal("0"),
    rounding_steps: int = 1,
) -> Decimal:
    """Return the PLN envelope implied by percentage and money rounding."""
    if rounding_steps < 1:
        raise ValueError("rounding_steps must be >= 1")
    percentage_component = total * precision_pp / Decimal("200")
    extra_money_rounding = Decimal(rounding_steps - 1) * Decimal("0.005")
    return money(base + percentage_component + extra_money_rounding)


def _candidate(
    total: Decimal,
    center: Decimal,
    low: Decimal,
    high: Decimal,
    base: Decimal,
) -> tuple[Decimal, Decimal]:
    center_amount = money(total * center)
    low_amount = money(total * max(Decimal("0"), low))
    high_amount = money(total * min(Decimal("1"), high))
    return center_amount, max(
        abs(center_amount - low_amount), abs(high_amount - center_amount)
    ) + base


def _signature_candidates(
    *,
    total: Decimal,
    work: Decimal,
    non_ip: Decimal,
    percentage: Decimal,
    method: str,
    base: Decimal,
    w_precision_pp: Decimal,
    percentage_precision_pp: Decimal,
    expected_w_percent: Decimal,
    reported_w_percent: Decimal | None,
) -> dict[str, tuple[Decimal, Decimal]]:
    time_share = (work - non_ip) / work
    p_half = percentage_precision_pp / Decimal("200")
    p_low = max(Decimal("0"), percentage - p_half)
    p_high = min(Decimal("1"), percentage + p_half)
    w_half = w_precision_pp / Decimal("200")
    result = {
        "invoice_percentage_once": _candidate(total, percentage, p_low, p_high, base),
        "invoice_percentage_squared": _candidate(
            total, percentage * percentage, p_low * p_low, p_high * p_high, base
        ),
        "full_revenue": (money(total), base),
    }
    raw = {
        "conditional_product": time_share * percentage,
        "disjoint_components": percentage - non_ip / work,
        "time_only": time_share,
    }
    for name, share in raw.items():
        if not Decimal("0") <= share <= Decimal("1"):
            continue
        center = share
        if name == method:
            center = (
                reported_w_percent / Decimal("100")
                if reported_w_percent is not None
                else expected_w_percent / Decimal("100")
            )
        result[name] = _candidate(total, center, center - w_half, center + w_half, base)
    return result


def _closest_signature(candidates: Mapping[str, tuple[Decimal, Decimal]], actual: Decimal) -> str:
    matches: list[tuple[Decimal, Decimal, str]] = []
    for name, (value, tolerance) in candidates.items():
        distance = abs(value - actual)
        if distance <= tolerance:
            normalized = distance / tolerance if tolerance else distance
            matches.append((normalized, distance, name))
    return min(matches)[2] if matches else "unclassified"


def audit_revenue_allocation(
    streams: Iterable[Mapping[str, Any]], *, tolerance: float = 0.02
) -> list[AllocationFinding]:
    """Audit independent invoice/project streams with rounding-aware envelopes."""
    base = money(tolerance)
    findings: list[AllocationFinding] = []
    signatures: list[tuple[str, str]] = []
    for index, record in enumerate(streams):
        month = str(record.get("month", record.get("miesiac", index + 1)))
        stream_id = str(record.get("stream_id", record.get("allocation_id", ""))).strip()
        label = f"{month}/{stream_id}" if stream_id else month
        total = money(_nonnegative("total_revenue", record.get("total_revenue", 0)))
        ip = money(_nonnegative("reported_ip_revenue", record.get("reported_ip_revenue", 0)))
        non = money(
            _nonnegative(
                "reported_non_ip_revenue",
                record.get("reported_non_ip_revenue", total - ip),
            )
        )
        rounding_steps = int(record.get("rounding_steps", 1))
        split_allowed = amount_tolerance(total, base=base, rounding_steps=rounding_steps)
        if abs(ip + non - total) > split_allowed:
            findings.append(
                AllocationFinding(
                    "REVENUE_SPLIT_DOES_NOT_BALANCE",
                    label,
                    total,
                    ip + non,
                    f"allowed={split_allowed}",
                )
            )

        work = _positive("work_hours", record.get("work_hours", 0))
        non_ip = _nonnegative("non_ip_hours", record.get("non_ip_hours", 0))
        percentage = _nonnegative(
            "invoice_percentage", record.get("invoice_percentage", 100)
        ) / Decimal("100")
        method = str(record.get("w_method", "conditional_product"))
        exact_w_percent = calculate_w_share(
            float(work), float(non_ip), float(percentage * 100), method=method
        ) * Decimal("100")
        expected_raw = _first(record, "expected_w_percent", "expected_W")
        expected_w = (
            _nonnegative("expected_w_percent", expected_raw)
            if expected_raw is not None
            else exact_w_percent
        )
        reported_raw = _first(
            record,
            "reported_w_percent",
            "reported_W",
            "w_percent",
            "W",
            "wartosc_W",
            "wartość_W",
        )
        reported_w = (
            _nonnegative("reported_w_percent", reported_raw) if reported_raw is not None else None
        )
        if expected_w > 100 or (reported_w is not None and reported_w > 100):
            raise ValueError("W percentage must not exceed 100")
        w_precision = _positive(
            "w_precision_pp",
            record.get("w_precision_pp", record.get("W_precision_pp", 0.01)),
        )
        percentage_precision = _positive(
            "invoice_percentage_precision_pp",
            record.get("invoice_percentage_precision_pp", 0.01),
        )
        if reported_w is not None and abs(expected_w - reported_w) > w_precision / 2 + Decimal(
            "0.0000001"
        ):
            findings.append(
                AllocationFinding(
                    "W_VALUE_MISMATCH",
                    label,
                    expected_w,
                    reported_w,
                    f"precision_pp={w_precision}",
                )
            )

        if reported_w is None:
            used_w = _round_to_quantum(expected_w, w_precision)
            expected_allowed = amount_tolerance(
                total,
                base=base,
                precision_pp=w_precision,
                rounding_steps=rounding_steps,
            )
        else:
            used_w = reported_w
            expected_allowed = amount_tolerance(total, base=base, rounding_steps=rounding_steps)
        expected = money(total * used_w / Decimal("100"))
        candidates = _signature_candidates(
            total=total,
            work=work,
            non_ip=non_ip,
            percentage=percentage,
            method=method,
            base=amount_tolerance(total, base=base, rounding_steps=rounding_steps),
            w_precision_pp=w_precision,
            percentage_precision_pp=percentage_precision,
            expected_w_percent=expected_w,
            reported_w_percent=reported_w,
        )
        signature = (
            method if abs(expected - ip) <= expected_allowed else _closest_signature(candidates, ip)
        )
        if abs(ip - total) <= split_allowed and used_w < 100:
            signature = "full_revenue"
        signatures.append((label, signature))
        if abs(expected - ip) > expected_allowed:
            findings.append(
                AllocationFinding(
                    "REVENUE_ALLOCATION_MISMATCH",
                    label,
                    expected,
                    ip,
                    (
                        f"declared W method={method}; observed signature={signature}; "
                        f"allowed={expected_allowed}; W precision={w_precision} pp"
                    ),
                )
            )
        if signature == "invoice_percentage_squared" and percentage not in {0, 1}:
            findings.append(
                AllocationFinding(
                    "INVOICE_PERCENTAGE_DOUBLE_APPLIED",
                    label,
                    expected,
                    ip,
                    f"invoice percentage precision={percentage_precision} pp",
                )
            )
        if signature == "full_revenue" and used_w < 100:
            findings.append(
                AllocationFinding("FULL_REVENUE_DESPITE_NON_IP_SHARE", label, expected, ip)
            )

    meaningful = [signature for _, signature in signatures if signature != "unclassified"]
    counts = Counter(meaningful)
    if len(counts) > 1:
        findings.append(
            AllocationFinding(
                "ALLOCATION_METHOD_SWITCH",
                None,
                detail=", ".join(f"{name}={count}" for name, count in sorted(counts.items())),
            )
        )
    return findings
