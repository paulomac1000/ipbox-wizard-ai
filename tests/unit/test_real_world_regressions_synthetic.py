from __future__ import annotations

import re
from pathlib import Path

import yaml

from tests.llm.oracle import compute_reference

SCENARIO_DIR = Path(__file__).parents[1] / "llm" / "scenarios"
REGRESSION_SCENARIOS = (32, *range(46, 56))


def _load(number: int) -> dict:
    path = next(SCENARIO_DIR.glob(f"{number:02d}_*.yaml"))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_new_regressions_are_synthetic_and_contain_no_obvious_identifiers() -> None:
    for number in REGRESSION_SCENARIOS:
        path = next(SCENARIO_DIR.glob(f"{number:02d}_*.yaml"))
        text = path.read_text(encoding="utf-8")
        assert "syntety" in text.casefold() or number in {49, 50, 51, 53, 54, 55}
        assert not re.search(r"(?<![\d.])\d{10,11}(?![\d.])", text)
        assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        assert "ul. " not in text.casefold()


def test_historical_2019_uses_health_tax_credit() -> None:
    result = compute_reference(_load(46))
    assert result["status"] == "FINAL"
    assert result["result"]["podatek"]["health_tax_credit_used"] == 300
    assert result["tests"]["TEST_6"] == "PASS"


def test_pre_2022_simultaneous_br_is_stopped() -> None:
    result = compute_reference(_load(47))
    assert result["status"] == "STOPPED"
    assert "STOP_13" in result["stops_reviews"]["stops"]


def test_pit_like_2024_cascade_is_reproduced_without_personal_numbers() -> None:
    result = compute_reference(_load(48))
    tax = result["result"]["podatek"]
    assert result["status"] == "FINAL"
    assert tax["podatek_IP"] == 9000
    assert tax["podatek_NIE_finalny"] == 0
    assert tax["termomodernization_carry_over"] == 9000


def test_double_percentage_and_method_switch_fail_closed() -> None:
    double = compute_reference(_load(49))
    switch = compute_reference(_load(50))
    assert set(double["stops_reviews"]["stops"]) >= {"STOP_09", "STOP_10"}
    assert set(switch["stops_reviews"]["stops"]) >= {"STOP_09", "STOP_10", "STOP_11"}
    assert "INVOICE_PERCENTAGE_DOUBLE_APPLIED" in double["stops_reviews"]["warnings"]
    assert "ALLOCATION_METHOD_SWITCH" in switch["stops_reviews"]["warnings"]


def test_equal_grand_totals_do_not_hide_return_ledger_shift() -> None:
    result = compute_reference(_load(51))
    assert result["status"] == "STOPPED"
    assert "STOP_12" in result["stops_reviews"]["stops"]


def test_monthly_pool_rounding_preserves_cents_and_nexus_evidence() -> None:
    result = compute_reference(_load(52))
    assert result["status"] == "FINAL"
    assert result["stops_reviews"]["stops"] == []
    assert result["result"]["koszty_roczne"]["IP"] == 100.0
    assert result["result"]["koszty_roczne"]["NIE"] == 200.03
    assert result["result"]["nexus_koszty"]["A"] == 100.0
    assert result["result"]["klucz_MIX"]["metoda"] == "przychodowa_w_dacie_kosztu"
    assert result["result"]["klucz_MIX"]["źródło_ref"] == "SYNTHETIC-KIS-REFERENCE"
    assert result["result"]["klucz_MIX"]["rounding_granularity"] == "monthly_pool"
    assert [item["ip_amount"] for item in result["classifications"]] == [33.34, 33.33, 33.33]
    assert sum(item["rounding_adjustment"] for item in result["classifications"]) == 0.01
    assert all(item["nexus_evidence"] for item in result["classifications"])


def test_year_boundaries_and_rounded_disjoint_w() -> None:
    assert "STOP_14" in compute_reference(_load(53))["stops_reviews"]["stops"]
    assert "STOP_16" in compute_reference(_load(54))["stops_reviews"]["stops"]
    clean = compute_reference(_load(55))
    assert clean["status"] == "FINAL"
    assert clean["stops_reviews"]["stops"] == []
    assert clean["monthly_W"] == [{"miesiąc": "2025-01", "wartość": 68.72}]
    assert clean["result"]["przychody_roczne"] == {"IP": 15874.32, "NIE": 9725.68}


def test_private_non_kup_produces_source_and_return_correction_preview() -> None:
    result = compute_reference(_load(32))
    assert result["status"] == "STOPPED"
    assert set(result["stops_reviews"]["stops"]) == {
        "SOURCE_KPIR_REQUIRES_CORRECTION",
        "STOP_12",
    }
    assert result["source_ledger_audit"] == {
        "status": "REQUIRES_CORRECTION",
        "reported_costs": 3400.0,
        "raw_input_costs": 3400.0,
        "deductible_costs": 3000.0,
        "excluded_recorded_costs": 400.0,
        "correction_delta": 400.0,
    }
    preview = result["correction_preview"]
    assert preview["status"] == "AVAILABLE"
    assert preview["source_kpir_correction_required"] is True
    assert preview["return_correction_required"] is True
    assert preview["relief_adjustment_required"] is True
    assert preview["tax_unchanged_only_if_reliefs_updated"] is True
    assert preview["corrected_total_tax"] == 900.0
    assert preview["corrected_overpayment"] == 4100.0
    assert preview["thermomodernization_used"] == 4000.0
    assert preview["thermomodernization_carry_over"] == 1000.0
