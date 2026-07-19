from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from tests.llm.evaluator import Evaluator
from tests.llm.oracle import (
    ScenarioError,
    compute_reference,
    derive_decision_codes,
    validate_scenario,
)
from tests.llm.output_schema import DECISION_JSON_SCHEMA, OUTPUT_JSON_SCHEMA
from tests.llm.runner import (
    LLMTestRunner,
    build_decision_protocol,
    build_tool_context,
)

SCENARIOS = sorted((Path(__file__).parents[1] / "llm/scenarios").glob("*.yaml"))


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def scenario(name: str) -> dict:
    return load(next(path for path in SCENARIOS if path.stem == name))


def decision_for(reference: dict) -> dict:
    return {
        "status": reference["status"],
        "stops": reference["stops_reviews"]["stops"],
        "reviews": reference["stops_reviews"]["reviews"],
    }


def test_exact_scenario_set_and_contracts() -> None:
    assert len(SCENARIOS) == 48
    ids = []
    for path in SCENARIOS:
        loaded = load(path)
        validate_scenario(loaded)
        ids.append(loaded["meta"]["id"])
        assert not loaded["meta"].get("skip")
        assert loaded["assertions"]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("scenario_path", SCENARIOS, ids=lambda path: path.stem)
def test_oracle_output_matches_schema_and_self_evaluates(scenario_path: Path) -> None:
    loaded = load(scenario_path)
    reference = compute_reference(loaded)
    schema_validated = {key: value for key, value in reference.items() if key != "decision_facts"}
    errors = list(Draft202012Validator(OUTPUT_JSON_SCHEMA["schema"]).iter_errors(schema_validated))
    assert errors == []
    assert reference["decision_facts"]
    assert all(isinstance(value, bool) for value in reference["decision_facts"].values())
    failures, _ = Evaluator(loaded).evaluate(reference)
    assert failures == []


def test_oracle_regressions() -> None:
    by_id = {path.stem: compute_reference(load(path)) for path in SCENARIOS}
    assert by_id["23_loss_carry_forward"]["result"]["przychody_roczne"]["IP"] == 18000
    assert by_id["23_loss_carry_forward"]["result"]["podatek"]["podatek_IP"] == 896
    assert by_id["29_edge_related_parties_nexus_0"]["result"]["podatek"]["podatek_IP"] == 0
    assert by_id["30_edge_related_parties_nexus_mixed"]["result"]["nexus"] == 0.337037
    assert by_id["39_multi_project_weighted_W"]["monthly_W"][0]["wartość"] == 74.0
    assert by_id["44_mix_revenue_key_kis"]["result"]["klucz_MIX"]["metoda"] == (
        "przychodowa_roczna"
    )
    assert by_id["45_multi_ip_two_stage"]["result"]["alokacja_multi_ip"]["allocations"] == [
        {"ip": "IP_A", "amount": 3000.0},
        {"ip": "IP_B", "amount": 5000.0},
    ]


@pytest.mark.parametrize(
    ("name", "expected_stops", "expected_reviews"),
    [
        ("14_lump_sum_ineligible_check", {"STOP_01"}, set()),
        ("18_logic_zero_work_hours", {"STOP_04"}, {"REVIEW_09"}),
        ("38_verify_missing_kpir_data", {"STOP_08"}, {"REVIEW_09"}),
        ("42_stop_08_no_documentation", {"STOP_08"}, {"REVIEW_09"}),
        (
            "45_multi_ip_two_stage",
            set(),
            {"REVIEW_04", "REVIEW_16", "REVIEW_17"},
        ),
    ],
)
def test_atomic_decision_facts_prevent_stop_cascades(
    name: str,
    expected_stops: set[str],
    expected_reviews: set[str],
) -> None:
    result = compute_reference(scenario(name))
    assert set(result["stops_reviews"]["stops"]) == expected_stops
    assert set(result["stops_reviews"]["reviews"]) == expected_reviews
    assert set(result["stops_reviews"]["stops"]) == derive_decision_codes(
        result["decision_facts"]
    )[0]


def test_scenario_validation_errors() -> None:
    valid = scenario("01_basic_linear")
    cases = []

    missing_year = deepcopy(valid)
    missing_year["input"].pop("rok")
    cases.append(missing_year)

    bad_months = deepcopy(valid)
    bad_months["input"]["miesiace"] = None
    cases.append(bad_months)

    bad_client = deepcopy(valid)
    bad_client["input"]["kontrahenci"] = ["bad"]
    cases.append(bad_client)

    bad_multi_ip = deepcopy(valid)
    bad_multi_ip["input"]["alokacja_multi_ip"] = {"przychody_IP": {}}
    cases.append(bad_multi_ip)

    for case in cases:
        with pytest.raises(ScenarioError):
            validate_scenario(case)


def test_build_tool_context_and_protocol_are_authoritative() -> None:
    reference = compute_reference(scenario("51_return_ledger_classification_shift_stop"))
    context = build_tool_context(reference)
    assert context == {
        "expected_decision": {
            "status": "STOPPED",
            "stops": ["STOP_12"],
            "reviews": ["REVIEW_09"],
        }
    }
    protocol = build_decision_protocol()
    assert "Copy expected_decision.status exactly" in protocol
    assert "A STOP never moves, suppresses, or converts a REVIEW code" in protocol


def test_output_schema_rejects_crossed_stop_review_codes() -> None:
    validator = Draft202012Validator(DECISION_JSON_SCHEMA["schema"])
    crossed = {
        "status": "STOPPED",
        "stops": ["REVIEW_09"],
        "reviews": ["STOP_12"],
    }
    assert list(validator.iter_errors(crossed))


def test_runner_parse_decision_is_strict() -> None:
    runner = LLMTestRunner(None)
    valid = {"status": "STOPPED", "stops": ["STOP_12"], "reviews": ["REVIEW_09"]}
    assert runner.parse_decision(yaml.safe_dump(valid, default_flow_style=True)) == valid

    invalid_values = [
        "```json\n{}\n```",
        '{"status":"FINAL","stops":["STOP_12"],"reviews":[]}',
        '{"status":"STOPPED","stops":["REVIEW_09"],"reviews":[]}',
        '{"status":"STOPPED","stops":["STOP_12","STOP_12"],"reviews":[]}',
    ]
    for raw in invalid_values:
        with pytest.raises(ValueError):
            runner.parse_decision(raw)
