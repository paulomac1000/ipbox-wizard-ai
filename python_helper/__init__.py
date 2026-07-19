"""Public deterministic helpers for the IP Box wizard."""

from . import tax_year_rules as _tax_year_rules
from .allocation_audit import (
    AllocationFinding,
    allocate_mix_at_cost_date,
    audit_revenue_allocation,
    calculate_w_percent,
    calculate_w_share,
    reconcile_return_to_ledger,
)
from .tax_cascade import calculate_tax_for_year
from .tax_year_rules import (
    TaxYearRules,
    ThermomodernizationLot,
    apply_thermomodernization_lots,
    calculate_scale_tax,
    get_tax_year_rules,
    reconcile_correction_settlement,
    supported_years,
    validate_year_amounts,
)

# Keep the historical import path working. Python loads this package before a
# direct ``python_helper.tax_year_rules`` import, so callers receive the fixed
# cascade while the year-rule catalogue remains backwards compatible.
_tax_year_rules.calculate_tax_for_year = calculate_tax_for_year

__all__ = [
    "AllocationFinding",
    "TaxYearRules",
    "ThermomodernizationLot",
    "allocate_mix_at_cost_date",
    "apply_thermomodernization_lots",
    "audit_revenue_allocation",
    "calculate_scale_tax",
    "calculate_tax_for_year",
    "calculate_w_percent",
    "calculate_w_share",
    "get_tax_year_rules",
    "reconcile_correction_settlement",
    "reconcile_return_to_ledger",
    "supported_years",
    "validate_year_amounts",
]
