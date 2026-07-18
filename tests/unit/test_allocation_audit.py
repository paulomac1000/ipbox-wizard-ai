from __future__ import annotations

import pytest

from python_helper.allocation_audit import (
    allocate_mix_at_cost_date,
    audit_revenue_allocation,
    calculate_w_percent,
    reconcile_return_to_ledger,
)


def test_w_semantics_are_explicit() -> None:
    assert calculate_w_percent(160, 16, 80, method="conditional_product") == 72.0
    assert calculate_w_percent(160, 16, 80, method="disjoint_components") == 70.0
    assert calculate_w_percent(160, 16, 80, method="time_only") == 90.0


@pytest.mark.parametrize(
    "args",
    [
        (0, 0, 100, "conditional_product"),
        (100, 101, 100, "conditional_product"),
        (100, 10, 101, "conditional_product"),
        (100, 90, 10, "disjoint_components"),
        (100, 10, 100, "bad"),
    ],
)
def test_w_invalid_semantics_fail(args) -> None:
    with pytest.raises(ValueError):
        calculate_w_percent(args[0], args[1], args[2], method=args[3])


def test_detects_double_percentage_and_silent_switch() -> None:
    findings = audit_revenue_allocation(
        [
            {
                "month": "2025-01",
                "total_revenue": 10000,
                "reported_ip_revenue": 6400,
                "reported_non_ip_revenue": 3600,
                "work_hours": 160,
                "non_ip_hours": 16,
                "invoice_percentage": 80,
                "w_method": "disjoint_components",
            },
            {
                "month": "2025-02",
                "total_revenue": 10000,
                "reported_ip_revenue": 10000,
                "reported_non_ip_revenue": 0,
                "work_hours": 160,
                "non_ip_hours": 16,
                "invoice_percentage": 100,
                "w_method": "disjoint_components",
            },
        ]
    )
    codes = {finding.code for finding in findings}
    assert "INVOICE_PERCENTAGE_DOUBLE_APPLIED" in codes
    assert "FULL_REVENUE_DESPITE_NON_IP_SHARE" in codes
    assert "ALLOCATION_METHOD_SWITCH" in codes
    assert "REVENUE_ALLOCATION_MISMATCH" in codes


def test_clean_revenue_allocation_has_no_findings() -> None:
    findings = audit_revenue_allocation(
        [
            {
                "month": "2024-01",
                "total_revenue": 10000,
                "reported_ip_revenue": 7000,
                "reported_non_ip_revenue": 3000,
                "work_hours": 160,
                "non_ip_hours": 16,
                "invoice_percentage": 80,
                "w_method": "disjoint_components",
            }
        ]
    )
    assert findings == []


def test_split_must_balance() -> None:
    codes = {
        finding.code
        for finding in audit_revenue_allocation(
            [
                {
                    "month": "x",
                    "total_revenue": 100,
                    "reported_ip_revenue": 50,
                    "reported_non_ip_revenue": 40,
                    "work_hours": 100,
                    "non_ip_hours": 50,
                    "invoice_percentage": 100,
                    "w_method": "time_only",
                }
            ]
        )
    }
    assert "REVENUE_SPLIT_DOES_NOT_BALANCE" in codes


def test_return_reconciliation_detects_classification_shift_even_when_totals_match() -> (
    None
):
    findings = reconcile_return_to_ledger(
        {
            "ip_revenue": 80000,
            "non_ip_revenue": 20000,
            "ip_cost": 8000,
            "non_ip_cost": 2000,
        },
        {
            "ip_revenue": 75000,
            "non_ip_revenue": 25000,
            "ip_cost": 7500,
            "non_ip_cost": 2500,
        },
    )
    codes = {finding.code for finding in findings}
    assert "RETURN_IP_REVENUE_MISMATCH" in codes
    assert "RETURN_REVENUE_CLASSIFICATION_SHIFT" in codes
    assert "RETURN_COST_CLASSIFICATION_SHIFT" in codes
    assert "RETURN_TOTAL_REVENUE_MISMATCH" not in codes


def test_return_reconciliation_detects_total_mismatch() -> None:
    codes = {
        finding.code
        for finding in reconcile_return_to_ledger(
            {"ip_revenue": 50, "non_ip_revenue": 50, "ip_cost": 10, "non_ip_cost": 10},
            {"ip_revenue": 50, "non_ip_revenue": 40, "ip_cost": 10, "non_ip_cost": 9},
        )
    }
    assert "RETURN_TOTAL_REVENUE_MISMATCH" in codes
    assert "RETURN_TOTAL_COST_MISMATCH" in codes


def test_cost_date_allocation_uses_each_month_ratio_and_preserves_cents() -> None:
    result = allocate_mix_at_cost_date(
        [
            {"month": "2024-01", "amount": 100.01},
            {"month": "2024-02", "amount": 50},
        ],
        {
            "2024-01": {"ip": 80, "total": 100},
            "2024-02": {"ip": 20, "total": 100},
        },
    )
    assert result["method"] == "przychodowa_w_dacie_kosztu"
    assert result["ip_total"] == 90.01
    assert result["non_ip_total"] == 60.0
    assert result["ip_total"] + result["non_ip_total"] == 150.01


def test_cost_date_allocation_rejects_missing_or_invalid_denominator() -> None:
    with pytest.raises(ValueError):
        allocate_mix_at_cost_date([{"month": "x", "amount": 1}], {})
    with pytest.raises(ValueError):
        allocate_mix_at_cost_date(
            [{"month": "x", "amount": 1}],
            {"x": {"ip": 0, "total": 0}},
        )
    with pytest.raises(ValueError):
        allocate_mix_at_cost_date(
            [{"month": "x", "amount": 1}],
            {"x": {"ip": 2, "total": 1}},
        )
