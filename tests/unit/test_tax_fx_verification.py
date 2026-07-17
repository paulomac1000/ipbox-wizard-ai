from __future__ import annotations

import math

import pytest

import python_helper.ipbox_calculator as calc
from python_helper.ipbox_calculator import (
    calculate_overpayment,
    convert_fx_invoice,
    get_nbp_rate,
    tax_cascade,
    verify_ip_tax,
    verify_kpir_balance,
    verify_private_costs,
    verify_zus_no_double_dip,
)


def test_tax_cascade_linear_and_scale() -> None:
    linear = tax_cascade(
        10000,
        20000,
        1,
        "liniowy_19%",
        ikze=1000,
        thermomodernization_pool=2000,
    )
    assert linear["non_ip_base_rounded"] == 7000
    assert linear["ip_tax"] == 1000
    assert linear["thermomodernization_carry_over"] == 0
    scale = tax_cascade(30000, 10000, 1, "skala", extra_income_scale=100000)
    assert scale["total_tax"] >= scale["ip_tax"]


@pytest.mark.parametrize(
    "name",
    [
        "previous_non_ip_business_losses",
        "social_security_deduction",
        "health_contribution_deduction",
        "ikze",
        "donations",
        "internet_tax_relief",
        "rehabilitative_relief_income",
        "rd_relief_non_ip",
        "rd_relief_ip",
        "rd_relief_limit",
        "thermomodernization_pool",
        "child_tax_credit",
        "extra_income_scale",
    ],
)
def test_tax_cascade_validates_all_deductions(name: str) -> None:
    kwargs = {name: math.nan}
    with pytest.raises(ValueError):
        tax_cascade(1, 1, 1, "liniowy_19%", **kwargs)
    kwargs[name] = -1
    with pytest.raises(ValueError):
        tax_cascade(1, 1, 1, "liniowy_19%", **kwargs)


def test_tax_cascade_contract_errors() -> None:
    with pytest.raises(ValueError):
        tax_cascade(1, 1, 2, "liniowy_19%")
    with pytest.raises(ValueError):
        tax_cascade(1, 1, 1, "bad")
    with pytest.raises(ValueError, match="exceeds rd_relief_limit"):
        tax_cascade(100, 100, 1, "liniowy_19%", rd_relief_ip=1)


def test_tax_cascade_rejects_reliefs_not_available_for_linear_tax() -> None:
    for field in (
        "donations",
        "internet_tax_relief",
        "rehabilitative_relief_income",
        "child_tax_credit",
    ):
        with pytest.raises(ValueError, match="unsupported relief for linear tax"):
            tax_cascade(10000, 0, 0, "liniowy_19%", **{field: 1})


def test_tax_cascade_validates_personal_relief_limits_and_combined_return() -> None:
    with pytest.raises(ValueError, match="cannot exceed 760"):
        tax_cascade(20000, 0, 0, "skala", internet_tax_relief=760.01)
    with pytest.raises(ValueError, match="6% income limit"):
        tax_cascade(10000, 0, 0, "skala", donations=600.01)
    combined = tax_cascade(
        10000,
        0,
        0,
        "skala",
        extra_income_scale=100000,
        ikze=1000,
        child_tax_credit=100,
    )
    assert combined["non_ip_base_rounded"] == 109000
    assert combined["non_ip_tax_final"] == 9380
    assert combined["extra_income_scale_included"] == 100000
    with pytest.raises(ValueError, match="separate scale-return"):
        tax_cascade(10000, 0, 0, "liniowy_19%", extra_income_scale=1000)


def test_tax_cascade_applies_supported_scale_reliefs() -> None:
    result = tax_cascade(
        50000,
        20000,
        0.5,
        "skala",
        donations=1000,
        internet_tax_relief=760,
        rd_relief_non_ip=2000,
        rd_relief_ip=1000,
        rd_relief_limit=3000,
    )
    assert result["non_ip_base_rounded"] == 46240
    assert result["non_ip_tax_final"] == 1949
    # PIT/IP position 19 is deducted before applying the nexus in position 20.
    assert result["rd_relief_ip_used"] == 1000
    assert result["rd_relief_non_ip_used"] == 2000
    assert result["rd_relief_carry_over"] == 0
    assert result["ip_base_rounded"] == 9500
    assert result["ip_tax"] == 475


def test_overpayment_paths_and_validation() -> None:
    assert calculate_overpayment(100, 200) == {"type": "overpayment", "amount": 100}
    assert calculate_overpayment(200, 100) == {"type": "amount_due", "amount": 100}
    assert calculate_overpayment(100, 100) == {"type": "settled", "amount": 0}
    with pytest.raises(ValueError):
        calculate_overpayment(-1, 1)


def test_verification_helpers() -> None:
    assert verify_kpir_balance(100, 50, 100.5, 49.5)["status"] == "PASS"
    assert verify_kpir_balance(100, 50, 90, 50)["status"] == "FAIL"
    assert verify_private_costs(0)["status"] == "PASS"
    assert verify_private_costs(1)["status"] == "FAIL"
    assert verify_zus_no_double_dip(True, 1, False, 0)["status"] == "FAIL"
    assert verify_zus_no_double_dip(False, 0, False, 0)["status"] == "PASS"
    assert verify_ip_tax(1000, 1, 1000, 50)["status"] == "PASS"
    assert verify_ip_tax(1000, 1, 1000, 49)["status"] == "FAIL"


class FakeResponse:
    def __init__(self, status: int, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


def test_get_nbp_rate_walks_back(monkeypatch) -> None:
    calls = []

    def get(url, timeout):
        calls.append(url)
        if len(calls) == 1:
            return FakeResponse(404)
        return FakeResponse(200, {"rates": [{"mid": 4.25}]})

    import requests

    monkeypatch.setattr(requests, "get", get)
    assert get_nbp_rate("USD", "2025-01-05") == 4.25
    assert len(calls) == 2


def test_get_nbp_rate_handles_errors(monkeypatch) -> None:
    import requests

    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(500))
    assert get_nbp_rate("USD", "2025-01-05") is None
    with pytest.raises(ValueError):
        get_nbp_rate("US", "2025-01-05")
    with pytest.raises(ValueError):
        get_nbp_rate("USD", "bad")
    with pytest.raises(ValueError):
        get_nbp_rate("USD", "2025-01-05", -1)


def test_convert_fx_invoice_success_and_missing_payment_rate(monkeypatch) -> None:
    rates = iter([4.0, 4.1])
    monkeypatch.setattr(calc, "get_nbp_rate", lambda *a, **k: next(rates))
    result = convert_fx_invoice(100, "USD", "2025-01-02", "2025-01-03")
    assert result["base_revenue_pln"] == 400
    assert result["exchange_rate_difference"] == 10
    rates = iter([4.0, None])
    monkeypatch.setattr(calc, "get_nbp_rate", lambda *a, **k: next(rates))
    result = convert_fx_invoice(100, "USD", "2025-01-02", "2025-01-03")
    assert "error" in result


def test_convert_fx_invoice_contract_errors(monkeypatch) -> None:
    monkeypatch.setattr(calc, "get_nbp_rate", lambda *a, **k: None)
    with pytest.raises(ValueError, match="payment_date"):
        convert_fx_invoice(100, "USD", "2025-01-02")
    with pytest.raises(ValueError):
        convert_fx_invoice(-1, "USD", "2025-01-02")
    with pytest.raises(ValueError):
        convert_fx_invoice(1, "USD", "2025-01-02", method="bad")
    with pytest.raises(ValueError):
        convert_fx_invoice(1, "USD", "2025-01-02", method="cash")
    with pytest.raises(ValueError):
        convert_fx_invoice(1, "USD", "bad")
    with pytest.raises(ValueError):
        convert_fx_invoice(1, "USD", "2025-01-03", "2025-01-02")


def test_health_contribution_is_deducted_once_from_linear_income() -> None:
    result = tax_cascade(10000, 0, 0, "liniowy_19%", health_contribution_deduction=1000)
    assert result["non_ip_base_rounded"] == 9000
    assert result["non_ip_tax_final"] == 1710
    assert any(step["step"] == "Health contribution" for step in result["deduction_steps"])


def test_health_contribution_rejected_for_scale() -> None:
    with pytest.raises(ValueError, match="only for linear"):
        tax_cascade(10000, 0, 0, "skala", health_contribution_deduction=1000)
