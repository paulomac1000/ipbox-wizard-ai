from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from tests.llm.evaluator import Evaluator
from tests.llm.oracle import ScenarioError, compute_reference, validate_scenario
from tests.llm.output_schema import OUTPUT_JSON_SCHEMA
from tests.llm.runner import LLMTestRunner, build_tool_context

SCENARIOS = sorted((Path(__file__).parents[1] / "llm/scenarios").glob("*.yaml"))


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_exact_scenario_set_and_contracts() -> None:
    assert len(SCENARIOS) == 36
    ids = []
    for path in SCENARIOS:
        scenario = load(path)
        validate_scenario(scenario)
        ids.append(scenario["meta"]["id"])
        assert not scenario["meta"].get("skip")
        assert scenario["assertions"]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("scenario_path", SCENARIOS, ids=lambda p: p.stem)
def test_oracle_output_matches_schema_and_self_evaluates(scenario_path: Path) -> None:
    scenario = load(scenario_path)
    reference = compute_reference(scenario)
    errors = list(Draft202012Validator(OUTPUT_JSON_SCHEMA["schema"]).iter_errors(reference))
    assert errors == []
    failures, _ = Evaluator(scenario).evaluate(reference)
    assert failures == []


def test_oracle_regressions() -> None:
    by_id = {p.stem: compute_reference(load(p)) for p in SCENARIOS}
    assert by_id["23_loss_carry_forward"]["result"]["przychody_roczne"]["IP"] == 18000
    assert by_id["23_loss_carry_forward"]["result"]["podatek"]["podatek_IP"] == 896
    assert by_id["29_edge_related_parties_nexus_0"]["result"]["podatek"]["podatek_IP"] == 0
    assert by_id["30_edge_related_parties_nexus_mixed"]["result"]["nexus"] == 0.337037
    assert by_id["39_multi_project_weighted_W"]["monthly_W"][0]["wartość"] == 74.0
    assert by_id["44_mix_revenue_key_kis"]["result"]["klucz_MIX"]["metoda"] == "przychodowa_roczna"
    assert by_id["45_multi_ip_two_stage"]["result"]["alokacja_multi_ip"]["allocations"] == [
        {"ip": "IP_A", "amount": 3000.0},
        {"ip": "IP_B", "amount": 5000.0},
    ]


def test_evaluator_is_fail_closed_for_missing_fields() -> None:
    scenario = load(next(p for p in SCENARIOS if p.stem == "01_basic_linear"))
    reference = compute_reference(scenario)
    broken = deepcopy(reference)
    del broken["tests"]["TEST_7"]
    failures, _ = Evaluator(scenario).evaluate(broken)
    assert any(f["type"] == "test_oracle_mismatch" for f in failures)
    broken = deepcopy(reference)
    broken["result"]["nexus"] = None
    failures, _ = Evaluator(scenario).evaluate(broken)
    assert any(f["type"] == "nexus_mismatch" for f in failures)
    broken = deepcopy(reference)
    broken["classifications"] = []
    failures, _ = Evaluator(scenario).evaluate(broken)
    assert any(f["type"] == "classification_keys" for f in failures)


def test_test_key_space_alias_is_understood() -> None:
    scenario = load(next(p for p in SCENARIOS if p.stem == "01_basic_linear"))
    reference = compute_reference(scenario)
    reference["tests"] = {key.replace("_", " "): value for key, value in reference["tests"].items()}
    failures, _ = Evaluator(scenario).evaluate(reference)
    assert failures == []


def test_invalid_scenario_contracts() -> None:
    scenario = load(SCENARIOS[0])
    for mutation in (
        lambda x: x.pop("meta"),
        lambda x: x["input"].pop("rok"),
        lambda x: x["input"].pop("forma_opodatkowania"),
        lambda x: x.update(assertions={}),
        lambda x: x["input"].pop("polityka_alokacji"),
    ):
        broken = deepcopy(scenario)
        mutation(broken)
        with pytest.raises(ScenarioError):
            validate_scenario(broken)


def test_runner_tool_context_excludes_final_codes() -> None:
    scenario = load(SCENARIOS[0])
    reference = compute_reference(scenario)
    context = build_tool_context(reference)
    assert "stops_reviews" not in context
    assert "status" not in context
    assert context["validation_facts"]["TEST_1"] is True
    prompt = LLMTestRunner(None).build_prompt("algorithm", scenario)
    assert "deterministic_tool_output" in prompt
    assert "zwróć tylko json" in prompt.lower()


def test_oracle_stops_when_no_qualifying_ip_revenue() -> None:
    scenario = load(next(p for p in SCENARIOS if p.stem == "40_mixed_ip_clause"))
    scenario = deepcopy(scenario)
    for client in scenario["input"]["kontrahenci"]:
        client["klauzula_IP"] = False
    for month in scenario["input"]["miesiace"]:
        for invoice in month["faktury"]:
            invoice["kwalifikuje_IP"] = False
    reference = compute_reference(scenario)
    assert reference["status"] == "STOPPED"
    assert reference["stops_reviews"]["stops"] == ["STOP_03"]
    assert reference["result"]["podatek"]["podatek_IP"] == 0
