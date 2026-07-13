import pytest

from python_helper.ipbox_calculator import (
    verify_ip_tax,
    verify_kpir_balance,
    verify_no_double_social_security,
    verify_overpayment,
    verify_private_costs,
    verify_tax_cascade,
)


class TestVerificationTests:
    """Testy weryfikacyjne dla gotowych deklaracji (Faza 8)."""

    @pytest.mark.unit
    @pytest.mark.P0
    def test_kpir_balance_pass(self):
        """TC-VT-001: Zgodność sum przychodów i kosztów."""
        res = verify_kpir_balance(
            ip_revenue_sum=100.0,
            non_ip_revenue_sum=200.0,
            net_fx_diff=0,
            kpir_revenue=300.0,
            ip_costs_sum=50.0,
            non_ip_costs_sum=50.0,
            kpir_costs_net=100.0
        )
        assert res["status"] == "PASS"

    @pytest.mark.unit
    @pytest.mark.P0
    def test_no_double_social_security_pass(self):
        """TC-VT-013: Poprawny anty-dubel."""
        # Scenario A: In KPiR, not in PIT
        assert verify_no_double_social_security(in_kpir=True, pit_deduction=0, monthly_costs_sum=1500)["status"] == "PASS"
        # Scenario B: Not in KPiR, in PIT
        assert verify_no_double_social_security(in_kpir=False, pit_deduction=1500, monthly_costs_sum=0)["status"] == "PASS"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_verify_cascade_validation(self):
        # Pass
        assert verify_tax_cascade(100, 50)["status"] == "PASS"
        # Fail: negative base
        assert verify_tax_cascade(-1, 50)["status"] == "FAIL"
        # Fail: negative carry-over
        assert verify_tax_cascade(100, -1)["status"] == "FAIL"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_verify_ip_tax_verification(self):
        # Income 100k, Nexus 0.5 -> Base 50k, Tax 2500
        assert verify_ip_tax(100000, 0.5, 50000, 2500)["status"] == "PASS"
        # Fail: mismatch
        assert verify_ip_tax(100000, 0.5, 50000, 3000)["status"] == "FAIL"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_verify_overpayment_verification(self):
        # Advances 10000, Tax 8000 -> Result 2000
        assert verify_overpayment(10000, 8000, 2000)["status"] == "PASS"
        # Fail: beyond tolerance
        assert verify_overpayment(10000, 8000, 2500)["status"] == "FAIL"

    @pytest.mark.unit
    @pytest.mark.P2
    def test_kpir_balance_costs_mismatch(self):
        res = verify_kpir_balance(
            ip_revenue_sum=100.0,
            non_ip_revenue_sum=200.0,
            net_fx_diff=0,
            kpir_revenue=300.0,
            ip_costs_sum=50.0,
            non_ip_costs_sum=50.0,
            kpir_costs_net=150.0 # mismatch
        )
        assert res["status"] == "FAIL"

    @pytest.mark.unit
    @pytest.mark.P2
    def test_verify_private_costs_forbidden(self):
        """TC-VT-002: Prywatne koszty nie mogą być w IP."""
        # Non-direct costs present alongside IP costs -> leak detected
        res = verify_private_costs(50)
        assert res["status"] == "FAIL"

        # Clean case: no non-direct costs
        res = verify_private_costs(0)
        assert res["status"] == "PASS"

        # Clean case: non-direct sum below tolerance
        res = verify_private_costs(0.01)
        assert res["status"] == "PASS"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_verify_private_costs_negative_raises(self):
        """TC-VT-XXX: Negative costs must raise ValueError."""
        with pytest.raises(ValueError, match="private_costs_allocated_to_ip"):
            verify_private_costs(-1)

    @pytest.mark.unit
    @pytest.mark.P1
    def test_verify_private_costs_nan_raises(self):
        """TC-VT-XXX: NaN must raise ValueError."""
        with pytest.raises(ValueError, match="private_costs_allocated_to_ip"):
            verify_private_costs(float("nan"))

    @pytest.mark.unit
    @pytest.mark.P1
    def test_verify_private_costs_inf_raises(self):
        """TC-VT-XXX: Infinity must raise ValueError."""
        with pytest.raises(ValueError, match="private_costs_allocated_to_ip"):
            verify_private_costs(float("inf"))

    @pytest.mark.unit
    @pytest.mark.P0
    def test_anti_double_dip_fail(self):
        """TC-VT-014: Fail when ZUS is in both KPiR and PIT."""
        res = verify_no_double_social_security(in_kpir=True, pit_deduction=1000, monthly_costs_sum=0)
        assert res["status"] == "FAIL"

    @pytest.mark.unit
    @pytest.mark.P0
    def test_anti_double_dip_pit_path_fail(self):
        """Fail when ZUS deducted in PIT but also appears in costs."""
        res = verify_no_double_social_security(in_kpir=False, pit_deduction=1000, monthly_costs_sum=500)
        assert res["status"] == "FAIL"
