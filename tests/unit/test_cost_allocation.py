import pytest
from python_helper.ipbox_calculator import allocate_costs_monthly, CostItem, AllocationPolicy

class TestCostAllocation:
    """Testy alokacji kosztów (Faza 3.3)."""

    @pytest.mark.unit
    @pytest.mark.P0
    def test_allocation_order(self):
        """Weryfikacja kolejności alokacji."""
        items = [
            CostItem("Serwer MIX", 1000.0, basket="MIX"),
            CostItem("Kawa NON", 100.0, basket="NON"),
            CostItem("Mandat EXCLUDED", 500.0, basket="EXCLUDED"),
        ]
        policy = AllocationPolicy(
            policy_id="test",
            mix_method="czasowa_W",
            mix_key=0.9,
            source="księgowa",
            justification="W = 90%",
        )
        res = allocate_costs_monthly(items, allocation_policy=policy)
        
        # Costs IP = MIX * 0.9 = 900
        # Costs NON = NON_direct (100) + MIX * 0.1 (100) = 200
        assert res["costs_ip"] == 900.0
        assert res["costs_non"] == 200.0
        assert res["excluded"] == 500.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_direct_ip_costs(self):
        """Dodatkowe koszty 100% IP."""
        items = [CostItem("Laptop MIX", 2000.0, basket="MIX")]
        ip_direct = [CostItem("Licencja 100% IP", 500.0, basket="IP")]
        
        policy = AllocationPolicy(
            policy_id="test",
            mix_method="czasowa_W",
            mix_key=0.5,
            source="księgowa",
            justification="W = 50%",
        )
        res = allocate_costs_monthly(items, allocation_policy=policy, ip_direct_costs=ip_direct)
        
        # Costs IP = IP_direct (500) + MIX * 0.5 (1000) = 1500
        assert res["costs_ip"] == 1500.0
