import pytest

from python_helper.ipbox_calculator import tax_cascade


class TestTaxCascade:
    """Testy kaskady odliczeń (P0: kolejność, P1: progi)."""

    @pytest.mark.unit
    @pytest.mark.P0
    def test_negative_tax_is_zero(self):
        """TC-TC-001: Tax cannot be negative."""
        # Income 10k, Deductions 20k -> Base 0
        res = tax_cascade(
            non_ip_income=10000.0,
            ip_income=0.0,
            nexus=1.0,
            tax_form="linear_19%",
            social_security_deduction=20000.0,
        )
        assert res["non_ip_tax_after_relief"] == 0
        assert res["non_ip_base_rounded"] == 0

    @pytest.mark.unit
    @pytest.mark.P0
    def test_cascade_order_preservation(self):
        """TC-TC-002: IKZE used before Thermomodernization."""
        # Income 10k, IKZE 6k, Termo 10k.
        # IKZE should consume 6k. Termo should consume 4k.
        res = tax_cascade(
            non_ip_income=10000.0,
            ip_income=0.0,
            nexus=1.0,
            tax_form="linear_19%",
            ikze=6000.0,
            thermomodernization_pool=10000.0,
        )
        # Check order in steps
        assert res["steps"][0]["step"] == "IKZE"
        assert res["steps"][1]["step"] == "Thermomodernization"
        assert res["thermo_used"] == 4000.0
        assert res["thermo_carry_over"] == 6000.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_scale_higher_bracket(self):
        """Tax on scale in second bracket (>120k)."""
        # Income 150k.
        # 120k * 12% - 3600 = 10800
        # 30k * 32% = 9600
        # Total = 20400
        res = tax_cascade(non_ip_income=150000.0, ip_income=0.0, nexus=1.0, tax_form="scale")
        assert res["non_ip_tax_before_relief"] == 20400

    @pytest.mark.unit
    @pytest.mark.P1
    def test_scale_with_external_income(self):
        """Scale with income from employment contract (UoP)."""
        # B2B 50k, UoP 100k. Total 150k.
        # Tax on 150k = 20400.
        # Proportionally for B2B: 20400 * (50/150) = 6800.
        res = tax_cascade(
            non_ip_income=50000.0,
            ip_income=0.0,
            nexus=1.0,
            tax_form="scale",
            extra_income_scale=100000.0,
        )
        assert res["non_ip_tax_before_relief"] == 6800

    @pytest.mark.unit
    @pytest.mark.P1
    def test_full_cascade_exhaustion(self):
        """Cascade exhausting income to zero."""
        res = tax_cascade(
            non_ip_income=10000.0,
            ip_income=100000.0,
            nexus=1.0,
            tax_form="linear_19%",
            ikze=6000.0,
            donations=2000.0,
            internet_tax_relief=760.0,
            thermomodernization_pool=10000.0,
        )
        assert res["non_ip_base_rounded"] == 0
        assert res["thermo_used"] == 10000.0 - 6000.0 - 2000.0 - 760.0
        assert res["ip_tax"] == 5000

    @pytest.mark.unit
    @pytest.mark.P1
    @pytest.mark.parametrize(
        "income,expected_tax",
        [
            (30000, 0),  # Tax-free (3600/0.12 = 30000)
            (40000, 1200),  # (40000*0.12 - 3600) = 1200
            (120000, 10800),  # (120000*0.12 - 3600) = 10800
            (200000, 36400),  # 10800 + 80000*0.32 = 10800 + 25600 = 36400
        ],
    )
    def test_scale_brackets_summary(self, income, expected_tax):
        res = tax_cascade(non_ip_income=income, ip_income=0, nexus=1.0, tax_form="scale")
        assert res["non_ip_tax_before_relief"] == expected_tax

    @pytest.mark.unit
    @pytest.mark.P1
    def test_negative_ip_income_zero_tax(self):
        """Negative IP income must produce zero IP tax."""
        res = tax_cascade(non_ip_income=0, ip_income=-10000, nexus=0.5, tax_form="linear_19%")
        assert res["ip_base_rounded"] == 0
        assert res["ip_tax"] == 0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_ip_with_nexus_reduction(self):
        res = tax_cascade(non_ip_income=0, ip_income=100000, nexus=0.5, tax_form="linear_19%")
        assert res["ip_base_rounded"] == 50000
        assert res["ip_tax"] == 2500

    @pytest.mark.unit
    @pytest.mark.P1
    def test_child_tax_credit_limit_on_tax(self):
        # Tax 1000, relief 2000 -> tax 0.
        res = tax_cascade(
            non_ip_income=38333.33, ip_income=0, nexus=1.0, tax_form="scale", child_tax_credit=2000
        )
        # Scale: 38333 * 0.12 - 3600 = 4600 - 3600 = 1000
        assert res["non_ip_tax_after_relief"] == 0
        assert res["used_child_credit"] == pytest.approx(1000, abs=1)

    @pytest.mark.unit
    @pytest.mark.P1
    def test_previous_losses_deduction(self):
        """Strata z lat ubiegłych odliczana przed wszystkim."""
        res = tax_cascade(
            non_ip_income=50000.0,
            ip_income=0.0,
            nexus=1.0,
            tax_form="linear_19%",
            previous_losses=30000.0,
        )
        # After losses: 50000 - 30000 = 20000 base; 20000 * 0.19 = 3800
        assert res["non_ip_base_rounded"] == 20000
        assert res["non_ip_tax_before_relief"] == 3800
        assert res["steps"][0]["step"] == "Losses from previous years"

    @pytest.mark.unit
    @pytest.mark.P2
    def test_scale_zero_income_no_error(self):
        """Skala z zerowym dochodem nie dzieli przez zero."""
        res = tax_cascade(non_ip_income=0, ip_income=0, nexus=1.0, tax_form="scale")
        assert res["non_ip_tax_before_relief"] == 0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_invalid_tax_form_raises_error(self):
        """TC-TC-VALID: Invalid tax_form raises ValueError."""
        with pytest.raises(ValueError, match="Invalid tax_form"):
            tax_cascade(non_ip_income=10000, ip_income=0, nexus=1.0, tax_form="liniowy_19%")
        with pytest.raises(ValueError, match="Invalid tax_form"):
            tax_cascade(non_ip_income=10000, ip_income=0, nexus=1.0, tax_form="linar_19%")
        with pytest.raises(ValueError, match="Invalid tax_form"):
            tax_cascade(non_ip_income=10000, ip_income=0, nexus=1.0, tax_form="skala")
        with pytest.raises(ValueError, match="Invalid tax_form"):
            tax_cascade(non_ip_income=10000, ip_income=0, nexus=1.0, tax_form="")
        res = tax_cascade(non_ip_income=10000, ip_income=0, nexus=1.0, tax_form="linear_19%")
        assert res is not None
        res = tax_cascade(non_ip_income=10000, ip_income=0, nexus=1.0, tax_form="scale")
        assert res is not None
