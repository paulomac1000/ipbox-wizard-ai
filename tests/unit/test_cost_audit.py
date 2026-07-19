from __future__ import annotations

import pytest

from python_helper.cost_audit import apply_cost_audit, validate_cost_policy


def _reference(*classifications: dict) -> dict:
    return {
        "result": {
            "przychody_roczne": {"IP": 1000.0, "NIE": 1000.0},
            "koszty_roczne": {"IP": 0.0, "NIE": 0.0, "MIX": 0.0, "WYKLUCZONE": 0.0},
            "nexus_koszty": {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "poza_nexus": 0.0},
            "nexus": 0.0,
            "dochód_IP": 1000.0,
            "dochód_NIE": 1000.0,
            "klucz_MIX": {
                "metoda": "przychodowa_w_dacie_kosztu",
                "źródło": "interpretacja_KIS",
                "wartość": None,
                "status": "FINAL",
            },
        },
        "classifications": list(classifications),
    }


def _mix_classification(description: str, *, evidence: str = "evidence") -> dict:
    return {
        "opis": description,
        "amount": 100.01,
        "basket": "MIX",
        "allocation_method": "przychodowa_w_dacie_kosztu",
        "allocation_source": "interpretacja_KIS",
        "allocation_key": 0.3333,
        "ip_amount": 33.33,
        "non_ip_amount": 66.68,
        "nexus_source": "own_br",
        "nexus_basket": "A",
        "nexus_amount": 33.33,
    }


def test_monthly_pool_preserves_the_pool_target_and_distributes_cents() -> None:
    scenario = {
        "input": {
            "polityka_alokacji": {
                "koszty_MIX": {
                    "źródło": "interpretacja_KIS",
                    "źródło_ref": "SYNTHETIC-KIS-REFERENCE",
                    "rounding_granularity": "monthly_pool",
                }
            },
            "miesiace": [
                {
                    "miesiac": "2025-06",
                    "koszty": [
                        {
                            "kwota": 100.01,
                            "nexus_evidence": f"evidence-{index}",
                            "nexus_basis": "allocated_ip_cost",
                        }
                        for index in range(3)
                    ],
                }
            ],
        }
    }
    reference = _reference(
        _mix_classification("A"),
        _mix_classification("B"),
        _mix_classification("C"),
    )

    audit, warnings = apply_cost_audit(scenario, reference)

    assert audit["status"] == "NOT_PROVIDED"
    assert warnings == []
    assert reference["result"]["koszty_roczne"]["IP"] == 100.0
    assert reference["result"]["koszty_roczne"]["NIE"] == 200.03
    assert reference["result"]["nexus_koszty"]["A"] == 100.0
    assert sum(item["rounding_adjustment"] for item in reference["classifications"]) == 0.01
    assert [item["ip_amount"] for item in reference["classifications"]] == [33.34, 33.33, 33.33]


def test_explicit_non_kup_overrides_non_ip_and_requires_source_ledger_correction() -> None:
    scenario = {
        "input": {
            "polityka_alokacji": {
                "koszty_MIX": {"źródło": "użytkownik"}
            },
            "podsumowanie_kpir": {"koszty": 400},
            "miesiace": [
                {
                    "miesiac": "2025-01",
                    "koszty": [
                        {
                            "kwota": 400,
                            "KUP": False,
                            "source_ledger_included": True,
                        }
                    ],
                }
            ],
        }
    }
    reference = _reference(
        {
            "opis": "Syntetyczny wydatek prywatny",
            "amount": 400.0,
            "basket": "NON",
            "allocation_method": "direct",
            "allocation_source": "",
            "allocation_key": 0.0,
            "ip_amount": 0.0,
            "non_ip_amount": 400.0,
            "nexus_source": "outside_nexus",
            "nexus_basket": "poza_nexus",
            "nexus_amount": 0.0,
        }
    )

    audit, warnings = apply_cost_audit(scenario, reference)

    assert reference["classifications"][0]["basket"] == "WYKLUCZONE"
    assert reference["result"]["koszty_roczne"]["NIE"] == 0.0
    assert reference["result"]["koszty_roczne"]["WYKLUCZONE"] == 400.0
    assert audit == {
        "status": "REQUIRES_CORRECTION",
        "reported_costs": 400.0,
        "raw_input_costs": 400.0,
        "deductible_costs": 0.0,
        "excluded_recorded_costs": 400.0,
        "correction_delta": 400.0,
    }
    assert {"NON_DEDUCTIBLE_COST_EXCLUDED", "SOURCE_KPIR_REQUIRES_CORRECTION"} <= set(
        warnings
    )


def test_kis_policy_requires_a_case_specific_source_reference() -> None:
    with pytest.raises(ValueError, match="requires źródło_ref"):
        validate_cost_policy(
            {
                "polityka_alokacji": {
                    "koszty_MIX": {"źródło": "interpretacja_KIS"}
                }
            }
        )


def test_qualified_nexus_without_evidence_is_downgraded_outside_nexus() -> None:
    scenario = {
        "input": {
            "polityka_alokacji": {
                "koszty_MIX": {"źródło": "użytkownik"}
            },
            "miesiace": [
                {"miesiac": "2025-01", "koszty": [{"kwota": 100}]}
            ],
        }
    }
    reference = _reference(_mix_classification("A", evidence=""))

    _, warnings = apply_cost_audit(scenario, reference)

    classification = reference["classifications"][0]
    assert classification["nexus_source"] == "outside_nexus"
    assert classification["nexus_basket"] == "poza_nexus"
    assert classification["nexus_amount"] == 0.0
    assert "NEXUS_EVIDENCE_MISSING" in warnings
