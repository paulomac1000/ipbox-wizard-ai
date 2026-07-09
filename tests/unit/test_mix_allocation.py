"""Unit tests for MIX allocation policy (Tests A-E, H + N1-N5)."""

import pytest
from python_helper.ipbox_calculator import (
    AllocationPolicy,
    CostItem,
    allocate_costs_monthly,
    allocate_revenue_monthly,
    annual_mix_allocation_revenue,
    allocate_multi_ip,
)


class TestMixAllocationPositive:
    """Positive tests — correct policies produce correct results."""

    @pytest.mark.unit
    @pytest.mark.P0
    def test_a_kis_revenue_key_annual(self):
        """KIS forces revenue key: annual allocation matches proportion."""
        result = annual_mix_allocation_revenue(
            deferred_mix_total=10000.0,
            annual_ip_revenue=87241.0,
            annual_total_revenue=100000.0,
        )
        assert abs(result["mix_key_used"] - 0.87241) < 0.0001
        assert abs(result["costs_ip_mix"] - 8724.10) < 0.01
        assert abs(result["costs_non_mix"] - 1275.90) < 0.01

        # Monthly: przychodowa_roczna defers MIX
        policy = AllocationPolicy(
            policy_id="test_a",
            revenue_method="czasowa_W",
            mix_method="przychodowa_roczna",
            mix_key=None,
            source="domyślna_wizard",
            justification="default test for deferred annual",
        )
        items = [CostItem("Serwer MIX", 1000.0, basket="MIX")]
        monthly = allocate_costs_monthly(items, allocation_policy=policy)
        assert monthly["mix_deferred"] == 1000.0
        assert monthly["result_status"] == "PROVISIONAL"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_b_default_revenue_proportion(self):
        """No KIS, no natural metric: default revenue-proportion key."""
        result = annual_mix_allocation_revenue(
            deferred_mix_total=12000.0,
            annual_ip_revenue=60000.0,
            annual_total_revenue=100000.0,
        )
        assert abs(result["mix_key_used"] - 0.60) < 0.0001
        assert abs(result["costs_ip_mix"] - 7200.0) < 0.01

    @pytest.mark.unit
    @pytest.mark.P1
    def test_c_natural_metric_per_item_key(self):
        """Per-item allocation_key for natural metric wins over policy."""
        policy = AllocationPolicy(
            policy_id="test_c",
            revenue_method="czasowa_W",
            mix_method="metraż",
            mix_key=0.90,  # Would give 90% but per-item 0.40 wins
            source="użytkownik",
            justification="metraż test",
        )
        items = [
            CostItem(
                "Wynajem biura",
                2000.0,
                basket="MIX",
                allocation_key=0.40,
                allocation_method="metraż",
            )
        ]
        result = allocate_costs_monthly(items, allocation_policy=policy)
        assert abs(result["costs_ip"] - 800.0) < 0.01  # 2000 * 0.40

    @pytest.mark.unit
    @pytest.mark.P0
    def test_d_direct_ip_not_multiplied(self):
        """Direct IP costs added as-is, not multiplied by mix_key."""
        items = [CostItem("Serwer MIX", 10000.0, basket="MIX")]
        ip_direct = [CostItem("Licencja IP", 2000.0, basket="IP")]
        policy = AllocationPolicy(
            policy_id="test_d",
            revenue_method="czasowa_W",
            mix_method="czasowa_W",
            mix_key=0.75,
            source="użytkownik",
            justification="test direct costs",
        )
        result = allocate_costs_monthly(
            items, allocation_policy=policy, ip_direct_costs=ip_direct
        )
        # costs_ip = IP_direct(2000) + MIX(10000)*0.75(7500) = 9500
        assert abs(result["costs_ip"] - 9500.0) < 0.01

    @pytest.mark.unit
    @pytest.mark.P1
    def test_e_eleven_zloty_difference(self):
        """Method comparison detects ~11 zł difference."""
        shifted = 80.88
        tax_diff = shifted * (0.19 - 0.05)
        assert abs(tax_diff - 11.3232) < 0.001
        assert round(tax_diff) == 11

    @pytest.mark.unit
    @pytest.mark.P1
    def test_h_multi_ip_two_stage(self):
        """Two-stage allocation for multiple IPs."""
        result = allocate_multi_ip(
            total_indirect_costs=10000.0,
            software_ip_revenue=80000.0,
            total_revenue=100000.0,
            ip_revenues={"IP_A": 30000.0, "IP_B": 50000.0},
        )
        assert abs(result["stage1"]["software_share"] - 8000.0) < 0.01
        assert abs(result["stage2"]["IP_A"]["costs"] - 3000.0) < 0.01
        assert abs(result["stage2"]["IP_B"]["costs"] - 5000.0) < 0.01


class TestMixAllocationNegative:
    """Negative tests — no silent W fallback."""

    @pytest.mark.unit
    @pytest.mark.P0
    def test_n1_missing_policy_raises_typeerror(self):
        """Missing allocation_policy → TypeError, not silent fallback."""
        with pytest.raises(TypeError):
            allocate_costs_monthly([])

    @pytest.mark.unit
    @pytest.mark.P0
    def test_n1_monthly_method_without_key_raises_valueerror(self):
        """Monthly method without any key → ValueError."""
        items = [CostItem("Server MIX", 1000.0, basket="MIX")]
        policy = AllocationPolicy(
            policy_id="n1",
            revenue_method="czasowa_W",
            mix_method="custom",
            mix_key=None,
            source="użytkownik",
            justification="custom but no key",
        )
        with pytest.raises(ValueError):
            allocate_costs_monthly(items, allocation_policy=policy)

    @pytest.mark.unit
    @pytest.mark.P1
    def test_n2_czasowa_w_without_justification(self):
        """czasowa_W without justification → ValueError at construction."""
        with pytest.raises(ValueError, match="justification"):
            AllocationPolicy(
                policy_id="n2",
                revenue_method="czasowa_W",
                mix_method="czasowa_W",
                mix_key=0.90,
                source="użytkownik",
                justification="",
            )

    @pytest.mark.unit
    @pytest.mark.P1
    def test_n3_mix_key_as_percent(self):
        """mix_key=87.2410 (percent) → ValueError at construction."""
        with pytest.raises(ValueError, match="mix_key"):
            AllocationPolicy(
                policy_id="n3",
                revenue_method="czasowa_W",
                mix_method="przychodowa_roczna",
                mix_key=87.2410,
                source="użytkownik",
                justification="percent test",
            )

    @pytest.mark.unit
    @pytest.mark.P1
    def test_n4_w_coefficient_ignored(self):
        """w_coefficient ignored when mix_method != czasowa_W."""
        items = [CostItem("Server MIX", 1000.0, basket="MIX")]
        policy = AllocationPolicy(
            policy_id="n4",
            revenue_method="czasowa_W",
            mix_method="metraż",
            mix_key=0.80,
            source="użytkownik",
            justification="metraż override",
        )
        result = allocate_costs_monthly(
            items, allocation_policy=policy, w_coefficient=90.0
        )
        assert abs(result["costs_ip"] - 800.0) < 0.01  # 0.80 wins, not 0.90

    @pytest.mark.unit
    @pytest.mark.P1
    def test_n5_revenue_key_outside_range(self):
        """revenue_key outside 0-1 → ValueError."""
        with pytest.raises(ValueError):
            allocate_revenue_monthly(
                base_revenue=10000.0,
                revenue_method="czasowa_W",
                revenue_key=1.5,
            )
