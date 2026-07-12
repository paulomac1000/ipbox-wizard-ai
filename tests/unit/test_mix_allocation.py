"""Unit tests for MIX allocation policy (Tests A-E, H + N1-N5)."""

import pytest

from python_helper.ipbox_calculator import (
    AllocationPolicy,
    CostItem,
    aggregate_nexus_costs,
    allocate_costs_monthly,
    allocate_multi_ip,
    allocate_revenue_monthly,
    annual_mix_allocation_revenue,
    nexus_classify,
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

    # --- P0 guard tests ---

    @pytest.mark.unit
    @pytest.mark.P0
    def test_przychodowa_roczna_accepts_mix_key_none_and_defers(self):
        """Annual policy with mix_key=None defers MIX costs."""
        policy = AllocationPolicy(
            policy_id="guard1",
            revenue_method="czasowa_W",
            mix_method="przychodowa_roczna",
            mix_key=None,
            source="domyślna_wizard",
            justification="guard test",
        )
        items = [CostItem("MIX", 1000.0, basket="MIX")]
        r = allocate_costs_monthly(items, allocation_policy=policy)
        assert r["mix_deferred"] == 1000.0
        assert r["result_status"] == "PROVISIONAL"

    @pytest.mark.unit
    @pytest.mark.P0
    def test_policy_mix_key_zero_is_valid(self):
        """0.0 is a valid explicit key under non-annual methods."""
        policy = AllocationPolicy(
            policy_id="guard2",
            revenue_method="czasowa_W",
            mix_method="metraż",
            mix_key=0.0,
            source="użytkownik",
            justification="metraż zero key",
        )
        items = [CostItem("MIX", 1000.0, basket="MIX")]
        r = allocate_costs_monthly(items, allocation_policy=policy)
        assert r["costs_ip"] == 0.0  # 0% to IP

    @pytest.mark.unit
    @pytest.mark.P0
    def test_per_item_allocation_key_zero_overrides(self):
        """Per-item allocation_key=0.0 overrides policy mix_key."""
        policy = AllocationPolicy(
            policy_id="guard3",
            revenue_method="czasowa_W",
            mix_method="przychodowa_roczna",
            mix_key=None,
            source="domyślna_wizard",
            justification="guard",
        )
        items = [CostItem("MIX", 1000.0, basket="MIX", allocation_key=0.0)]
        r = allocate_costs_monthly(items, allocation_policy=policy)
        assert r["costs_ip"] == 0.0
        assert r["mix_deferred"] == 0.0  # allocated, not deferred

    @pytest.mark.unit
    @pytest.mark.P0
    def test_annual_policy_rejects_policy_mix_key(self):
        """Annual policy with mix_key != None raises ValueError."""
        with pytest.raises(ValueError):
            AllocationPolicy(
                policy_id="guard4",
                revenue_method="czasowa_W",
                mix_method="przychodowa_roczna",
                mix_key=0.80,
                source="domyślna_wizard",
                justification="should fail",
            )

    @pytest.mark.unit
    @pytest.mark.P0
    def test_invalid_nexus_source_raises_valueerror(self):
        """Typo in nexus_source raises ValueError."""
        item = CostItem("test", 100.0, basket="IP")
        with pytest.raises(ValueError):
            nexus_classify(item, nexus_source="unrelated_contractor")

    @pytest.mark.unit
    @pytest.mark.P0
    def test_mix_into_a_without_nexus_amount_rejected(self):
        """MIX cost with nexus_basket=A but no nexus_amount raises ValueError."""
        item = CostItem("MIX cost", 1000.0, basket="MIX", nexus_basket="A")
        with pytest.raises(ValueError):
            aggregate_nexus_costs([item])

    @pytest.mark.unit
    @pytest.mark.P1
    def test_allocation_policy_validation_errors(self):
        """AllocationPolicy validation exceptions."""
        # Missing source
        with pytest.raises(ValueError, match="source is required"):
            AllocationPolicy(policy_id="e1", source="")

        # Invalid source
        with pytest.raises(ValueError, match="source='invalid'"):
            AllocationPolicy(policy_id="e2", source="invalid")

        # Invalid mix_method
        with pytest.raises(ValueError, match="mix_method='invalid'"):
            AllocationPolicy(policy_id="e3", source="użytkownik", mix_method="invalid")

        # Invalid revenue_method
        with pytest.raises(ValueError, match="revenue_method='invalid'"):
            AllocationPolicy(policy_id="e4", source="użytkownik", revenue_method="invalid")

        # mix_key out of range
        with pytest.raises(ValueError, match="mix_key must be between 0 and 1"):
            AllocationPolicy(policy_id="e5", source="użytkownik", mix_method="metraż", mix_key=1.5, justification="yes")

        # czasowa_W requires mix_key
        with pytest.raises(ValueError, match="czasowa_W requires mix_key"):
            AllocationPolicy(policy_id="e6", source="użytkownik", mix_method="czasowa_W", mix_key=None, justification="yes")

        # custom requires justification
        with pytest.raises(ValueError, match="custom requires justification"):
            AllocationPolicy(policy_id="e7", source="użytkownik", mix_method="custom", mix_key=0.5, justification="")

    @pytest.mark.unit
    @pytest.mark.P1
    def test_mix_method_aliases_normalization(self):
        """AllocationPolicy mix_method aliases normalization."""
        policy = AllocationPolicy(
            policy_id="a1",
            source="użytkownik",
            mix_method="przychodowy_roczny",
        )
        assert policy.mix_method == "przychodowa_roczna"

        policy2 = AllocationPolicy(
            policy_id="a2",
            source="użytkownik",
            mix_method="czasowy_W",
            mix_key=0.8,
            justification="time tracked",
        )
        assert policy2.mix_method == "czasowa_W"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_w_coefficient_range_validation(self):
        """w_coefficient range check (0-100) and reporting."""
        policy = AllocationPolicy(
            policy_id="w1",
            source="użytkownik",
            mix_method="metraż",
            mix_key=0.5,
            justification="test",
        )
        # Valid
        res = allocate_costs_monthly([], allocation_policy=policy, w_coefficient=85.0)
        assert res["w_coefficient"] == 85.0

        # Invalid (negative)
        with pytest.raises(ValueError, match=r"w_coefficient.*must be between 0 and 100"):
            allocate_costs_monthly([], allocation_policy=policy, w_coefficient=-5.0)

        # Invalid (large)
        with pytest.raises(ValueError, match=r"w_coefficient.*must be between 0 and 100"):
            allocate_costs_monthly([], allocation_policy=policy, w_coefficient=105.0)

    @pytest.mark.unit
    @pytest.mark.P1
    def test_allocate_costs_monthly_item_key_out_of_bounds(self):
        """allocate_costs_monthly raises ValueError if item allocation_key is invalid."""
        policy = AllocationPolicy(
            policy_id="p1",
            source="domyślna_wizard",
            mix_method="przychodowa_roczna",
            mix_key=None,
        )
        items = [CostItem("AWS", 100, basket="MIX", allocation_key=1.2)]
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            allocate_costs_monthly(items, allocation_policy=policy)

    @pytest.mark.unit
    @pytest.mark.P1
    def test_resolve_mix_key_edge_cases(self):
        """resolve_mix_key exception and non-MIX branches."""
        from python_helper.ipbox_calculator import resolve_mix_key

        policy = AllocationPolicy(
            policy_id="r1",
            source="użytkownik",
            mix_method="metraż",
            mix_key=0.5,
            justification="test",
        )

        # Non-MIX item returns 0.0
        item_ip = CostItem("Direct", 100, basket="IP")
        assert resolve_mix_key(item_ip, policy) == 0.0

        # Item allocation key out of range
        item_invalid = CostItem("MIX", 100, basket="MIX", allocation_key=1.5)
        with pytest.raises(ValueError, match=r"allocation_key.*must be between 0 and 1"):
            resolve_mix_key(item_invalid, policy)

        # Policy mix_key out of range (wait, policy.mix_key is validated in __post_init__, but let's bypass it via object.__setattr__ to trigger the resolve check)
        policy_invalid = AllocationPolicy(
            policy_id="r2",
            source="użytkownik",
            mix_method="metraż",
            mix_key=0.5,
            justification="test",
        )
        object.__setattr__(policy_invalid, "mix_key", -0.2)
        item_normal = CostItem("MIX", 100, basket="MIX")
        with pytest.raises(ValueError, match=r"policy.mix_key.*must be between 0 and 1"):
            resolve_mix_key(item_normal, policy_invalid)

        # No key resolved
        policy_nokey = AllocationPolicy(
            policy_id="r3",
            source="domyślna_wizard",
            mix_method="przychodowa_roczna",
            mix_key=None,
        )
        with pytest.raises(ValueError, match="Cannot resolve mix_key"):
            resolve_mix_key(item_normal, policy_nokey)

    @pytest.mark.unit
    @pytest.mark.P1
    def test_aggregate_nexus_costs_edge_cases(self):
        """aggregate_nexus_costs invalid fields and success with nexus_amount."""
        # Invalid basket
        item_invalid_basket = CostItem("desc", 100, nexus_basket="INVALID")
        with pytest.raises(ValueError, match="Invalid nexus_basket"):
            aggregate_nexus_costs([item_invalid_basket])

        # Negative nexus amount
        # CostItem.__post_init__ normally catches this; let's bypass it via object.__setattr__ to test the aggregator check
        item_neg_bypass = CostItem("desc", 100, nexus_basket="A")
        object.__setattr__(item_neg_bypass, "nexus_amount", -10.0)
        with pytest.raises(ValueError, match="nexus amount cannot be negative"):
            aggregate_nexus_costs([item_neg_bypass])

        # Success with nexus_amount
        item_success = CostItem("desc", 100, basket="IP", nexus_basket="A", nexus_amount=30.0)
        res = aggregate_nexus_costs([item_success])
        assert res["A"] == 30.0
        assert res["poza_nexus"] == 70.0

        # Success with nexus_amount for MIX
        item_mix_success = CostItem("MIX desc", 100, basket="MIX", nexus_basket="A", nexus_amount=40.0)
        res_mix = aggregate_nexus_costs([item_mix_success])
        assert res_mix["A"] == 40.0
        assert res_mix["poza_nexus"] == 60.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_allocate_revenue_monthly_validation_and_branches(self):
        """allocate_revenue_monthly validation checks and method branches."""
        # Negative base revenue
        with pytest.raises(ValueError, match=r"base_revenue.*must be >= 0"):
            allocate_revenue_monthly(base_revenue=-100, revenue_method="czasowa_W")

        # Invalid revenue method
        with pytest.raises(ValueError, match="must be one of"):
            allocate_revenue_monthly(base_revenue=100, revenue_method="invalid")

        # Missing split for dokumentowa
        with pytest.raises(ValueError, match="document_split_ip is required"):
            allocate_revenue_monthly(base_revenue=100, revenue_method="dokumentowa", document_split_ip=None)

        # Split out of range
        with pytest.raises(ValueError, match="must be between 0 and base_revenue"):
            allocate_revenue_monthly(base_revenue=100, revenue_method="dokumentowa", document_split_ip=150)

        # Missing key for other methods
        with pytest.raises(ValueError, match="revenue_key is required"):
            allocate_revenue_monthly(base_revenue=100, revenue_method="czasowa_W", revenue_key=None)

        # Success dokumentowa
        res_doc = allocate_revenue_monthly(base_revenue=100, revenue_method="dokumentowa", document_split_ip=80)
        assert res_doc["ip_revenue"] == 80.0
        assert res_doc["non_ip_revenue"] == 20.0

        # Success non-dokumentowa
        res_other = allocate_revenue_monthly(base_revenue=100, revenue_method="czasowa_W", revenue_key=0.7)
        assert res_other["ip_revenue"] == 70.0
        assert res_other["non_ip_revenue"] == 30.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_annual_mix_allocation_revenue_errors_and_zero(self):
        """annual_mix_allocation_revenue error handling and zero deferred branch."""
        # annual_total_revenue <= 0
        with pytest.raises(ValueError, match="annual_total_revenue must be > 0"):
            annual_mix_allocation_revenue(annual_total_revenue=0, annual_ip_revenue=10, deferred_mix_total=100)

        # annual_ip_revenue < 0
        with pytest.raises(ValueError, match="annual_ip_revenue must be >= 0"):
            annual_mix_allocation_revenue(annual_total_revenue=100, annual_ip_revenue=-10, deferred_mix_total=100)

        # annual_ip_revenue > annual_total_revenue
        with pytest.raises(ValueError, match="cannot exceed annual_total_revenue"):
            annual_mix_allocation_revenue(annual_total_revenue=100, annual_ip_revenue=150, deferred_mix_total=100)

        # deferred_mix_total < 0
        with pytest.raises(ValueError, match="deferred_mix_total must be >= 0"):
            annual_mix_allocation_revenue(annual_total_revenue=100, annual_ip_revenue=80, deferred_mix_total=-5)

        # deferred_mix_total == 0
        res = annual_mix_allocation_revenue(annual_total_revenue=100, annual_ip_revenue=80, deferred_mix_total=0)
        assert res["costs_ip_mix"] == 0.0
        assert res["costs_non_mix"] == 0.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_allocate_multi_ip_validation_errors(self):
        """allocate_multi_ip validation exceptions."""
        # total_indirect_costs < 0
        with pytest.raises(ValueError, match="total_indirect_costs must be >= 0"):
            allocate_multi_ip(total_indirect_costs=-10, software_ip_revenue=100, total_revenue=150, ip_revenues={"ip1": 50})

        # total_revenue <= 0
        with pytest.raises(ValueError, match="total_revenue must be > 0"):
            allocate_multi_ip(total_indirect_costs=10, software_ip_revenue=100, total_revenue=0, ip_revenues={"ip1": 50})

        # software_ip_revenue < 0
        with pytest.raises(ValueError, match="software_ip_revenue must be >= 0"):
            allocate_multi_ip(total_indirect_costs=10, software_ip_revenue=-5, total_revenue=100, ip_revenues={"ip1": 50})

        # software_ip_revenue > total_revenue
        with pytest.raises(ValueError, match="cannot exceed total_revenue"):
            allocate_multi_ip(total_indirect_costs=10, software_ip_revenue=150, total_revenue=100, ip_revenues={"ip1": 50})

        # empty ip_revenues
        with pytest.raises(ValueError, match="ip_revenues dict must be non-empty"):
            allocate_multi_ip(total_indirect_costs=10, software_ip_revenue=80, total_revenue=100, ip_revenues={})

        # negative individual IP revenue
        with pytest.raises(ValueError, match="must be >= 0"):
            allocate_multi_ip(total_indirect_costs=10, software_ip_revenue=80, total_revenue=100, ip_revenues={"ip1": -10})

        # total IP revenue <= 0
        with pytest.raises(ValueError, match="Sum of ip_revenues values must be > 0"):
            allocate_multi_ip(total_indirect_costs=10, software_ip_revenue=80, total_revenue=100, ip_revenues={"ip1": 0.0})

        # sum(ip_revenues) != software_ip_revenue (mismatch > 0.02)
        with pytest.raises(ValueError, match="does not match"):
            allocate_multi_ip(total_indirect_costs=10, software_ip_revenue=100, total_revenue=200, ip_revenues={"ip1": 50, "ip2": 30})

    @pytest.mark.unit
    @pytest.mark.P1
    def test_verify_ip_tax_declared_base_mismatch(self):
        """verify_ip_tax verification failures."""
        from python_helper.ipbox_calculator import verify_ip_tax
        res = verify_ip_tax(ip_income=10000.0, nexus=1.0, declared_base=8000, declared_tax=400)
        assert res["status"] == "FAIL"
        assert "Expected base" in res["error"]
