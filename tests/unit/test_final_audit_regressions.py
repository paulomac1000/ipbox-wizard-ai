"""Regressions for the final audit boundary and reporting contract."""

from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from python_helper.ipbox_calculator import calculate_w_coefficient
from scripts.check_cassette_policy import main as cassette_policy_main
from scripts.record_model import paid_cost_since, select_scenarios
from tests.llm.oracle import (
    ScenarioError,
    _recompute_kpir_balance_test,
    compute_reference,
    validate_scenario,
)
from tests.llm.runner import LLMTestRunner, build_tool_context
from tests.llm.test_scenarios import discover_scenarios

SCENARIOS = Path(__file__).resolve().parents[1] / "llm/scenarios"


def scenario(name: str) -> dict:
    return yaml.safe_load((SCENARIOS / f"{name}.yaml").read_text(encoding="utf-8"))


def test_cassette_policy_accepts_missing_and_empty_roots_but_rejects_partial(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    assert cassette_policy_main(missing) == 0

    empty = tmp_path / "empty"
    empty.mkdir()
    assert cassette_policy_main(empty) == 0

    partial = tmp_path / "partial"
    (partial / "unexpected-model").mkdir(parents=True)
    assert cassette_policy_main(partial) == 1


def test_numeric_boundaries_reject_booleans_and_numeric_strings() -> None:
    with pytest.raises(ValueError, match="must be a number"):
        calculate_w_coefficient(True, 0)

    loaded = deepcopy(scenario("01_basic_linear"))
    loaded["input"]["miesiace"][0]["faktury"][0]["kwota_PLN"] = "1000.00"
    with pytest.raises(ScenarioError, match="must be a number"):
        validate_scenario(loaded)


def test_incomplete_coverage_is_provisional_not_false_stop_03() -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    loaded["input"].pop("coverage")
    reference = compute_reference(loaded)
    assert reference["status"] == "PROVISIONAL"
    assert reference["stops_reviews"]["stops"] == []
    assert "REVIEW_19" in reference["stops_reviews"]["reviews"]

    for client in loaded["input"]["kontrahenci"]:
        client["klauzula_IP"] = False
    for month in loaded["input"]["miesiace"]:
        for invoice in month["faktury"]:
            invoice["kwalifikuje_IP"] = False
    reference = compute_reference(loaded)
    assert reference["status"] == "PROVISIONAL"
    assert "STOP_03" not in reference["stops_reviews"]["stops"]
    assert "REVIEW_19" in reference["stops_reviews"]["reviews"]


def test_complete_coverage_allows_stop_03() -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    for client in loaded["input"]["kontrahenci"]:
        client["klauzula_IP"] = False
    for month in loaded["input"]["miesiace"]:
        for invoice in month["faktury"]:
            invoice["kwalifikuje_IP"] = False
    reference = compute_reference(loaded)
    assert reference["status"] == "STOPPED"
    assert "STOP_03" in reference["stops_reviews"]["stops"]


def test_provisional_decision_is_a_first_class_runner_status() -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    loaded["input"].pop("coverage")
    reference = compute_reference(loaded)
    context = build_tool_context(reference)
    assert context["expected_decision"]["status"] == "PROVISIONAL"
    parsed = LLMTestRunner(None).parse_decision(
        json.dumps(context["expected_decision"], ensure_ascii=False)
    )
    assert parsed["status"] == "PROVISIONAL"

    with pytest.raises(ValueError, match="inconsistent with stops"):
        LLMTestRunner(None).parse_decision(
            json.dumps({"status": "PROVISIONAL", "stops": ["STOP_01"], "reviews": []})
        )


def test_final_report_contains_reproducibility_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPBOX_CALCULATED_AT", "2026-07-25T20:00:00Z")
    monkeypatch.setenv("IPBOX_CODE_REVISION", "audit-test-sha")
    reference = compute_reference(scenario("01_basic_linear"))
    meta = reference["calculation_meta"]
    assert meta["engine_version"] == "ipbox-wizard-ai"
    assert meta["rule_pack"] == "PL-PIT-IPBOX-2025"
    assert meta["rules_source_ids"]
    assert len(meta["input_hash"]) == 64
    assert meta["calculated_at"] == "2026-07-25T20:00:00Z"
    assert meta["code_revision"] == "audit-test-sha"


def test_description_heuristics_create_review_without_overriding_explicit_basket() -> None:
    explicit = deepcopy(scenario("01_basic_linear"))
    cost = explicit["input"]["miesiace"][0]["koszty"][0]
    cost["opis"] = "Integracja systemu z API NFZ"
    reference = compute_reference(explicit)
    assert reference["classifications"][0]["basket"] == "IP"
    assert "REVIEW_21" not in reference["stops_reviews"]["reviews"]

    candidate = deepcopy(explicit)
    cost = candidate["input"]["miesiace"][0]["koszty"][0]
    cost.pop("kategoria", None)
    cost.pop("koszyk", None)
    cost.pop("allocation_source", None)
    cost["nexus_source"] = "outside_nexus"
    cost.pop("nexus_evidence", None)
    cost.pop("nexus_amount", None)
    reference = compute_reference(candidate)
    assert reference["classifications"][0]["basket"] == "MIX"
    assert reference["status"] == "PROVISIONAL"
    assert "REVIEW_21" in reference["stops_reviews"]["reviews"]


def test_high_value_service_requires_review_instead_of_exclusion() -> None:
    loaded = deepcopy(scenario("01_basic_linear"))
    cost = loaded["input"]["miesiace"][0]["koszty"][0]
    cost.update({"opis": "Usługa audytu bezpieczeństwa", "kwota": 12500})
    cost.pop("kategoria", None)
    cost.pop("koszyk", None)
    cost.pop("allocation_source", None)
    cost["nexus_source"] = "outside_nexus"
    cost.pop("nexus_evidence", None)
    cost.pop("nexus_amount", None)
    reference = compute_reference(loaded)
    assert reference["classifications"][0]["basket"] == "MIX"
    assert reference["status"] == "PROVISIONAL"
    assert "REVIEW_20" in reference["stops_reviews"]["reviews"]


def test_paid_recording_scenario_selection_is_exact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = [tmp_path / "0.yaml", tmp_path / "01.yaml"]
    for path in paths:
        path.write_text("meta: {}\n", encoding="utf-8")
    assert select_scenarios(paths, "0") == [tmp_path / "0.yaml"]
    with pytest.raises(ValueError, match="No exact scenario"):
        select_scenarios(paths, "missing")

    monkeypatch.setenv("IPBOX_SCENARIO", "0")
    with pytest.raises(RuntimeError, match="no exact scenario"):
        discover_scenarios()
    monkeypatch.delenv("IPBOX_SCENARIO")


def test_global_paid_cost_counts_accepted_and_rejected_calls(tmp_path: Path) -> None:
    started = time.time() - 10
    cassette_root = tmp_path / "cassettes"
    model_dir = cassette_root / "model-a"
    model_dir.mkdir(parents=True)
    (model_dir / "accepted.yaml").write_text(
        "meta:\n  cost: 0.20\nresponse: ok\nparsed_response: {}\n",
        encoding="utf-8",
    )
    rejected_root = tmp_path / "rejected"
    rejected_dir = rejected_root / "model-a"
    rejected_dir.mkdir(parents=True)
    (rejected_dir / "rejected.json").write_text(
        json.dumps({"metadata": {"cost": 0.30}}),
        encoding="utf-8",
    )
    assert paid_cost_since(
        cassette_root,
        rejected_root,
        since=started,
    ) == pytest.approx(0.50)
    assert paid_cost_since(
        cassette_root,
        rejected_root,
        since=started,
        model="model-a",
    ) == pytest.approx(0.50)


def test_legacy_thermomodernization_pool_is_explicitly_provisional() -> None:
    loaded = deepcopy(scenario("27_termomodernizacja_full"))
    reliefs = loaded["input"]["ulgi"]
    reliefs.pop("termomodernizacja_loty")
    reliefs["termomodernizacja_pula"] = 53000
    reference = compute_reference(loaded)
    assert reference["status"] == "PROVISIONAL"
    assert "REVIEW_22" in reference["stops_reviews"]["reviews"]
    assert reference["result"]["podatek"]["thermomodernization_mode"] == "legacy_pool"
    assert reference["result"]["podatek"]["thermomodernization_evidence_status"] == "PROVISIONAL"


def test_kpir_balance_excludes_rows_explicitly_absent_from_source_ledger() -> None:
    input_data = {
        "podsumowanie_kpir": {"przychody": 0, "koszty": 100},
        "miesiace": [
            {
                "miesiac": "2025-01",
                "koszty": [
                    {"opis": "Recorded", "kwota": 100},
                    {
                        "opis": "Not present in source KPiR",
                        "kwota": 50,
                        "source_ledger_included": False,
                    },
                ],
            }
        ],
    }

    assert _recompute_kpir_balance_test(input_data) == "PASS"
