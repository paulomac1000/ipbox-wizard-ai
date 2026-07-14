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
        child_tax_credit=100,
    )
    assert linear["non_ip_base_rounded"] == 7000
    assert linear["ip_tax"] == 1000
    assert linear["thermomodernization_carry_over"] == 0
    scale = tax_cascade(30000, 10000, 1, "skala", extra_income_scale=100000)
    assert scale["total_tax"] >= scale["ip_tax"]


@pytest.mark.parametrize(
    "name",
    [
        "previous_losses",
        "social_security_deduction",
        "ikze",
        "donations",
        "internet_tax_relief",
        "rehabilitative_relief_income",
        "rd_relief",
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
    assert "error" in convert_fx_invoice(100, "USD", "2025-01-02")
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
