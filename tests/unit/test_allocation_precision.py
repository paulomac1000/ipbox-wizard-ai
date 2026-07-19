from __future__ import annotations

from python_helper.allocation_precision import audit_revenue_allocation


def _codes(rows: list[dict]) -> set[str]:
    return {finding.code for finding in audit_revenue_allocation(rows)}


def test_rounded_w_to_two_decimal_percentage_points_is_accepted() -> None:
    findings = audit_revenue_allocation(
        [
            {
                "month": "2024-01",
                "total_revenue": 23100,
                "reported_ip_revenue": 15874.32,
                "reported_non_ip_revenue": 7225.68,
                "work_hours": 168,
                "non_ip_hours": 22,
                "invoice_percentage": 81.8181818182,
                "w_method": "disjoint_components",
                "reported_w_percent": 68.72,
                "w_precision_pp": 0.01,
            }
        ]
    )
    assert findings == []


def test_dynamic_tolerance_accepts_rounded_w_when_only_precision_is_known() -> None:
    findings = audit_revenue_allocation(
        [
            {
                "month": "2024-01",
                "total_revenue": 23100,
                "reported_ip_revenue": 15874.32,
                "reported_non_ip_revenue": 7225.68,
                "work_hours": 168,
                "non_ip_hours": 22,
                "invoice_percentage": 81.8181818182,
                "w_method": "disjoint_components",
                "w_precision_pp": 0.01,
            }
        ]
    )
    assert findings == []


def test_rounded_percentage_detects_squared_signature_and_switch() -> None:
    found = _codes(
        [
            {
                "month": "2025-01",
                "total_revenue": 23100,
                "reported_ip_revenue": 15463.64,
                "reported_non_ip_revenue": 7636.36,
                "work_hours": 168,
                "non_ip_hours": 22,
                "invoice_percentage": 81.82,
                "invoice_percentage_precision_pp": 0.01,
                "w_method": "disjoint_components",
            },
            {
                "month": "2025-02",
                "total_revenue": 23100,
                "reported_ip_revenue": 23100,
                "reported_non_ip_revenue": 0,
                "work_hours": 168,
                "non_ip_hours": 22,
                "invoice_percentage": 100,
                "w_method": "disjoint_components",
            },
        ]
    )
    assert {
        "REVENUE_ALLOCATION_MISMATCH",
        "INVOICE_PERCENTAGE_DOUBLE_APPLIED",
        "FULL_REVENUE_DESPITE_NON_IP_SHARE",
        "ALLOCATION_METHOD_SWITCH",
    } <= found


def test_wrong_reported_w_is_not_hidden_by_amount_tolerance() -> None:
    found = _codes(
        [
            {
                "month": "2024-01",
                "total_revenue": 100000,
                "reported_ip_revenue": 70000,
                "reported_non_ip_revenue": 30000,
                "work_hours": 160,
                "non_ip_hours": 16,
                "invoice_percentage": 80,
                "w_method": "disjoint_components",
                "reported_w_percent": 70.10,
                "w_precision_pp": 0.01,
            }
        ]
    )
    assert "W_VALUE_MISMATCH" in found


def test_independent_stream_labels_are_preserved_in_findings() -> None:
    findings = audit_revenue_allocation(
        [
            {
                "month": "2025-01",
                "stream_id": "project-B",
                "total_revenue": 10000,
                "reported_ip_revenue": 10000,
                "reported_non_ip_revenue": 0,
                "work_hours": 100,
                "non_ip_hours": 20,
                "invoice_percentage": 100,
                "w_method": "time_only",
            }
        ]
    )
    assert any(finding.month == "2025-01/project-B" for finding in findings)
