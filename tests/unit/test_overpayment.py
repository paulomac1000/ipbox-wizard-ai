import pytest
from python_helper.ipbox_calculator import calculate_overpayment_or_underpayment

class TestOverpayment:
    """Testy obliczania nadpłaty/dopłaty (Faza 7.4)."""

    @pytest.mark.unit
    @pytest.mark.P1
    def test_overpayment(self):
        # Advances 10000, Tax 8000 -> 2000 overpayment
        res = calculate_overpayment_or_underpayment(10000.0, 8000.0)
        assert res["result"] == 2000.0
        assert res["type"] == "overpayment"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_underpayment(self):
        # Advances 5000, Tax 7000 -> 2000 underpayment (-2000)
        res = calculate_overpayment_or_underpayment(5000.0, 7000.0)
        assert res["result"] == -2000.0
        assert res["type"] == "underpayment"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_zero_balance(self):
        res = calculate_overpayment_or_underpayment(5000.0, 5000.0)
        assert res["result"] == 0.0
        assert res["type"] == "overpayment"

    @pytest.mark.unit
    @pytest.mark.P2
    def test_decimal_precision(self):
        res = calculate_overpayment_or_underpayment(10000.55, 10000.11)
        assert res["result"] == 0.44
        assert res["type"] == "overpayment"
