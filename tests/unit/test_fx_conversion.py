import pytest
from unittest.mock import patch
from python_helper.ipbox_calculator import convert_fx_invoice

class TestFXConversion:
    """Testy walutowe i różnic kursowych (Faza 4)."""

    @pytest.mark.unit
    @pytest.mark.P0
    @patch("python_helper.ipbox_calculator.get_nbp_rate")
    def test_fx_conversion_basic(self, mock_rate):
        # Invoice 1000 USD, Issued 2025-01-14, Paid 2025-01-20
        # Rate for 2025-01-13 (prev day): 4.30
        # Rate for 2025-01-19 (Sunday -> Friday 17th): 4.40
        # Exchange diff: (4.40-4.30) * 1000 = +100 PLN (NON-IP revenue)
        
        def side_effect(curr, date):
            if date in ["2025-01-13"]: return 4.30
            if date in ["2025-01-19", "2025-01-18", "2025-01-17"]: return 4.40
            return None
            
        mock_rate.side_effect = side_effect
        
        res = convert_fx_invoice(
            amount_currency=1000.0,
            currency="USD",
            issue_date="2025-01-14",
            payment_date="2025-01-20"
        )
        
        assert res["base_revenue_pln"] == 4300.0
        assert res["exchange_rate_difference"] == 100.0
        assert "NON" in res["info"]

    @pytest.mark.unit
    @pytest.mark.P0
    @patch("python_helper.ipbox_calculator.get_nbp_rate")
    def test_fx_conversion_negative_diff(self, mock_rate):
        # Rate drop -> NON-IP cost
        def side_effect(curr, date):
            if date in ["2025-01-13"]: return 4.30
            if date in ["2025-01-19", "2025-01-18", "2025-01-17"]: return 4.20
            return None
        mock_rate.side_effect = side_effect
        
        res = convert_fx_invoice(
            amount_currency=1000.0,
            currency="USD",
            issue_date="2025-01-14",
            payment_date="2025-01-20"
        )
        
        assert res["exchange_rate_difference"] == -100.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_cash_method_requires_payment_date(self):
        """Cash method without payment_date → error."""
        res = convert_fx_invoice(
            amount_currency=1000.0,
            currency="USD",
            issue_date="2025-01-14",
            method="cash",
        )
        assert "error" in res

    @pytest.mark.unit
    @pytest.mark.P1
    @patch("python_helper.ipbox_calculator.get_nbp_rate")
    def test_nbp_rate_unavailable_returns_error(self, mock_rate):
        """When NBP rate unavailable → error in result."""
        mock_rate.return_value = None
        res = convert_fx_invoice(
            amount_currency=1000.0,
            currency="USD",
            issue_date="2025-01-14",
        )
        assert "error" in res

    @pytest.mark.unit
    @pytest.mark.P1
    @patch("python_helper.ipbox_calculator.get_nbp_rate")
    def test_accrual_no_payment_date_zero_diff(self, mock_rate):
        """Accrual method without payment_date → no exchange rate difference."""
        mock_rate.return_value = 4.30
        res = convert_fx_invoice(
            amount_currency=1000.0,
            currency="USD",
            issue_date="2025-01-14",
        )
        assert res["exchange_rate_difference"] == 0.0
        assert res["difference_month"] is None
