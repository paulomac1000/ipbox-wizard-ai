import pytest
from python_helper.ipbox_calculator import (
    calculate_w_coefficient, 
    allocate_costs_monthly, 
    calculate_nexus, 
    tax_cascade, 
    calculate_overpayment_or_underpayment,
    CostItem
)

class TestIntegrationCalculator:
    """Pełny test integracyjny — od W do finalnego wyniku."""

    @pytest.mark.unit
    @pytest.mark.smoke
    def test_full_year_cycle_simplified(self):
        # 1. Calculate W (January)
        # 160h work, 16h non-IP -> W = 90%
        w_res = calculate_w_coefficient(160, 16)
        w_coeff = w_res["W"]
        
        # 2. Revenue and Costs (January)
        revenue = 20000.0
        income_ip_monthly = revenue * (w_coeff/100) # 18000
        income_non_monthly = revenue * (1 - w_coeff/100) # 2000
        
        items = [CostItem("Server", 1000.0, basket="MIX")]
        alloc = allocate_costs_monthly(items, w_coeff)
        # Cost IP = 1000 * 0.9 = 900
        # Cost NON = 1000 * 0.1 = 100
        
        doch_ip = income_ip_monthly - alloc["costs_ip"] # 18000 - 900 = 17100
        doch_non = income_non_monthly - alloc["costs_non"] # 2000 - 100 = 1900
        
        # 3. Assume same for 12 months
        doch_ip_annual = doch_ip * 12 # 205200
        doch_non_annual = doch_non * 12 # 22800
        
        # 4. NEXUS
        nexus_res = calculate_nexus(A=12000)
        nexus_val = nexus_res["nexus"] # 1.0
        
        # 5. Cascade
        cascade = tax_cascade(
            non_ip_income=doch_non_annual,
            ip_income=doch_ip_annual,
            nexus=nexus_val,
            tax_form="linear_19%",
            social_security_deduction=15000 
        )
        
        # Non-IP income after SS: 22800 - 15000 = 7800
        # Non-IP base: 7800
        # Non-IP tax: 7800 * 0.19 = 1482
        # IP base: 205200 * 1.0 = 205200
        # IP tax: 205200 * 0.05 = 10260
        # Total tax: 1482 + 10260 = 11742
        
        assert cascade["total_tax"] == 11742
        
        # 6. Overpayment
        final = calculate_overpayment_or_underpayment(15000, cascade["total_tax"])
        assert final["result"] == 15000 - 11742
