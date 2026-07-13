from unittest.mock import patch

import pytest

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
            if date in ["2025-01-13"]:
                return 4.30
            if date in ["2025-01-19", "2025-01-18", "2025-01-17"]:
                return 4.40
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
            if date in ["2025-01-13"]:
                return 4.30
            if date in ["2025-01-19", "2025-01-18", "2025-01-17"]:
                return 4.20
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

    @pytest.mark.unit
    @pytest.mark.P1
    @patch("python_helper.ipbox_calculator.get_nbp_rate")
    def test_cash_method_success(self, mock_rate):
        """Cash method with payment_date conversion."""
        mock_rate.return_value = 4.30
        res = convert_fx_invoice(
            amount_currency=1000.0,
            currency="USD",
            issue_date="2025-01-14",
            payment_date="2025-01-20",
            method="cash",
        )
        assert res["base_revenue_pln"] == 4300.0
        assert res["exchange_rate_difference"] == 0.0

    @pytest.mark.unit
    @pytest.mark.P1
    @patch("python_helper.ipbox_calculator.get_nbp_rate")
    def test_payment_rate_none_branch(self, mock_rate):
        """When payment rate is None, difference should be 0.0."""
        def side_effect(curr, date):
            if date == "2025-01-13":
                return 4.30
            return None
        mock_rate.side_effect = side_effect
        res = convert_fx_invoice(
            amount_currency=1000.0,
            currency="USD",
            issue_date="2025-01-14",
            payment_date="2025-01-20",
        )
        assert res["exchange_rate_difference"] == 0.0
        assert res["payment_rate"] is None

    @pytest.mark.unit
    @pytest.mark.P1
    @patch("requests.get")
    def test_get_nbp_rate_requests(self, mock_get):
        """Test get_nbp_rate requests branches (success, 404, exception)."""
        from unittest.mock import MagicMock

        from python_helper.ipbox_calculator import get_nbp_rate

        # Success
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"rates": [{"mid": 4.35}]}
        mock_get.return_value = mock_resp
        assert get_nbp_rate("USD", "2025-01-14") == 4.35

        # 404 fallback (weekend)
        mock_get.reset_mock()
        mock_resp_404 = MagicMock()
        mock_resp_404.status_code = 404
        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.json.return_value = {"rates": [{"mid": 4.32}]}
        mock_get.side_effect = [mock_resp_404, mock_resp_ok]
        assert get_nbp_rate("USD", "2025-01-12") == 4.32

        # Other status code
        mock_get.side_effect = None
        mock_resp_err = MagicMock()
        mock_resp_err.status_code = 500
        mock_get.return_value = mock_resp_err
        assert get_nbp_rate("USD", "2025-01-14") is None

        # Exception
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("API error")
        assert get_nbp_rate("USD", "2025-01-14") is None

    @pytest.mark.unit
    @pytest.mark.P1
    def test_cost_item_nexus_amount_validation(self):
        """CostItem nexus_amount validation bounds."""
        from python_helper.ipbox_calculator import CostItem

        # Valid
        item = CostItem(description="Valid", amount=100, nexus_amount=50)
        assert item.nexus_amount == 50

        # Invalid (negative)
        with pytest.raises(ValueError, match="must be between 0 and cost amount"):
            CostItem(description="Invalid neg", amount=100, nexus_amount=-10)

        # Invalid (greater than amount)
        with pytest.raises(ValueError, match="must be between 0 and cost amount"):
            CostItem(description="Invalid large", amount=100, nexus_amount=150)
