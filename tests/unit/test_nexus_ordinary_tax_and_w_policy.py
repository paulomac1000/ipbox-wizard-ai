from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from python_helper import calculate_tax_for_year
from tests.llm.oracle import ScenarioError, compute_reference
from tests.llm.oracle_adapter import w_method

SCENARIO_DIR = Path(__file__).parents[1] / "llm" / "scenarios"


def _scenario(number: int) -> dict:
    path = next(SCENARIO_DIR.glob(f"{number:02d}_*.yaml"))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_linear_taxes_nexus_remainder_at_ordinary_rate() -> None:
    result = calculate_tax_for_year(
        2025,
        non_ip_income=0,
        ip_income=10_000,
        nexus=0.65,
        tax_form="liniowy_19%",
    )

    assert result["qualified_ip_income"] == 6500.0
    assert result["ordinary_ip_income"] == 3500.0
    assert result["ip_base_rounded"] == 6500
    assert result["ordinary_base_rounded"] == 3500
    assert result["ip_tax"] == 325
    assert result["non_ip_tax_final"] == 665
    assert result["total_tax"] == 990


def test_nexus_zero_taxes_all_ip_income_at_ordinary_rate() -> None:
    result = calculate_tax_for_year(
        2025,
        non_ip_income=0,
        ip_income=5000,
        nexus=0,
        tax_form="liniowy_19%",
    )

    assert result["qualified_ip_income"] == 0.0
    assert result["ordinary_ip_income"] == 5000.0
    assert result["ip_tax"] == 0
    assert result["non_ip_tax_final"] == 950
    assert result["total_tax"] == 950


def test_scale_combines_nexus_remainder_with_ordinary_income() -> None:
    result = calculate_tax_for_year(
        2025,
        non_ip_income=10_000,
        ip_income=100_000,
        nexus=0.5,
        tax_form="skala",
    )

    assert result["ordinary_business_income_before_deductions"] == 60_000.0
    assert result["ordinary_base_rounded"] == 60_000
    assert result["non_ip_tax_final"] == 3600
    assert result["ip_tax"] == 2500
    assert result["total_tax"] == 6100


def test_current_non_ip_loss_offsets_nexus_remainder() -> None:
    result = calculate_tax_for_year(
        2025,
        non_ip_income=-5_000,
        ip_income=20_000,
        nexus=0.5,
        tax_form="liniowy_19%",
    )

    assert result["ordinary_ip_income"] == 10_000.0
    assert result["ordinary_business_income_before_deductions"] == 5_000.0
    assert result["ordinary_base_rounded"] == 5_000
    assert result["non_ip_tax_final"] == 950


def test_oracle_preserves_current_non_ip_loss_before_taxing_nexus_remainder() -> None:
    loaded = deepcopy(_scenario(30))
    loaded["input"]["kontrahenci"].append({"nazwa": "ClientB", "klauzula_IP": False})
    month = loaded["input"]["miesiace"][0]
    month["faktury"].append(
        {
            "kwota_PLN": 10_000,
            "kontrahent": "ClientB",
            "kwalifikuje_IP": False,
        }
    )
    month["koszty"].append(
        {
            "opis": "Syntetyczny koszt działalności NIE",
            "kwota": 15_000,
            "kategoria": "NIE",
            "nexus_source": "outside_nexus",
        }
    )

    result = compute_reference(loaded)
    tax = result["result"]["podatek"]
    expected_ordinary_base = round(
        result["result"]["dochód_NIE"] + tax["dochód_IP_poza_preferencją"]
    )

    assert result["result"]["dochód_NIE"] == -5_000
    assert tax["podstawa_zwykła"] == expected_ordinary_base


def test_scenario_with_nexus_zero_no_longer_erases_tax() -> None:
    result = compute_reference(_scenario(29))
    tax = result["result"]["podatek"]

    assert result["status"] == "FINAL"
    assert tax["dochód_IP_kwalifikowany"] == 0.0
    assert tax["dochód_IP_poza_preferencją"] == 5000.0
    assert tax["podatek_IP"] == 0
    assert tax["podatek_NIE_finalny"] == 950
    assert tax["podatek_całościowy"] == 950


def test_mixed_nexus_exposes_both_taxed_parts() -> None:
    result = compute_reference(_scenario(30))
    tax = result["result"]["podatek"]

    assert result["status"] == "FINAL"
    assert tax["podstawa_IP"] == 8931
    assert tax["podstawa_zwykła"] == 17569
    assert tax["podatek_IP"] == 447
    assert tax["podatek_NIE_finalny"] == 3338
    assert tax["podatek_całościowy"] == 3785


def test_missing_w_method_is_rejected_when_both_modifiers_are_active() -> None:
    ambiguous = {
        "miesiace": [
            {
                "miesiac": "2025-01",
                "ewidencja": {
                    "godziny_pracy": 160,
                    "godziny_nie_IP": 20,
                    "procent_faktury_IP": 80,
                },
            }
        ]
    }

    with pytest.raises(ScenarioError, match="W.metoda"):
        w_method(ambiguous)


def test_missing_w_method_is_safe_when_only_one_modifier_is_active() -> None:
    time_only = {
        "miesiace": [
            {
                "miesiac": "2025-01",
                "ewidencja": {
                    "godziny_pracy": 160,
                    "godziny_nie_IP": 20,
                    "procent_faktury_IP": 100,
                },
            }
        ]
    }
    invoice_only = deepcopy(time_only)
    invoice_only["miesiace"][0]["ewidencja"].update(
        godziny_nie_IP=0,
        procent_faktury_IP=80,
    )

    assert w_method(time_only) == "conditional_product"
    assert w_method(invoice_only) == "conditional_product"


def test_missing_nexus_evidence_is_visible_review_not_silent_false() -> None:
    scenario = _scenario(52)
    scenario["input"]["miesiace"][0]["koszty"][0].pop("nexus_evidence")

    result = compute_reference(scenario)

    assert result["status"] == "FINAL"
    assert "REVIEW_18" in result["stops_reviews"]["reviews"]
    assert "NEXUS_EVIDENCE_MISSING" in result["stops_reviews"]["warnings"]
    first = result["classifications"][0]
    assert first["nexus_basket"] == "poza_nexus"
    assert first["nexus_amount"] == 0.0


def test_private_description_is_review_candidate_not_automatic_kup_decision() -> None:
    scenario = _scenario(1)
    scenario["input"]["miesiace"][0]["koszty"][0]["opis"] = "Kawa do domu"

    result = compute_reference(scenario)

    candidate = next(item for item in result["classifications"] if item["opis"] == "Kawa do domu")
    assert candidate["basket"] == "IP"
    assert candidate["ip_amount"] > 0
    assert "NON_DEDUCTIBLE_CANDIDATE" in result["stops_reviews"]["warnings"]
    assert "SOURCE_KPIR_REQUIRES_CORRECTION" not in result["stops_reviews"]["stops"]


def test_missing_evidence_with_allocation_control_preserves_stop_08() -> None:
    scenario = _scenario(42)
    scenario["input"]["miesiace"][0]["kontrola_alokacji"] = {
        "przychod_IP": 20_000,
        "przychod_NIE": 0,
    }

    result = compute_reference(scenario)

    assert result["status"] == "STOPPED"
    assert "STOP_08" in result["stops_reviews"]["stops"]


def test_positive_fx_difference_is_included_in_kpir_revenue_balance() -> None:
    scenario = _scenario(3)
    scenario["input"]["podsumowanie_kpir"] = {
        "przychody": 20_150,
        "koszty": 500,
    }

    result = compute_reference(scenario)

    assert result["tests"]["TEST_1"] == "PASS"
    assert result["result"]["przychody_roczne"]["NIE"] == 150.0
