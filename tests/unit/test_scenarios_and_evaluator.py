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
from tests.llm.output_schema import OUTPUT_JSON_SCHEMA
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
    assert len(SCENARIOS) == 36
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
    reference = compute_reference(scenario(name))
    stops, reviews = derive_decision_codes(reference["decision_facts"])
    assert stops == expected_stops
    assert reviews == expected_reviews
    assert set(reference["stops_reviews"]["stops"]) == expected_stops
    assert set(reference["stops_reviews"]["reviews"]) == expected_reviews


def test_multi_ip_is_a_visible_review_fact() -> None:
    reference = compute_reference(scenario("45_multi_ip_two_stage"))
    assert reference["decision_facts"]["multiple_projects_or_ips"] is True
    assert reference["decision_facts"]["uses_kis_interpretation"] is True
    assert reference["decision_facts"]["kis_implementation_requires_confirmation"] is True


def test_meta_expected_reviews_cannot_change_oracle_truth() -> None:
    loaded = scenario("01_basic_linear")
    baseline = compute_reference(loaded)
    mutated = deepcopy(loaded)
    mutated["meta"]["expected_reviews"] = ["REVIEW_99"]
    observed = compute_reference(mutated)
    assert observed["decision_facts"] == baseline["decision_facts"]
    assert observed["stops_reviews"] == baseline["stops_reviews"]


def test_evaluator_is_fail_closed_for_missing_fields() -> None:
    loaded = scenario("01_basic_linear")
    reference = compute_reference(loaded)
    broken = deepcopy(reference)
    del broken["tests"]["TEST_7"]
    failures, _ = Evaluator(loaded).evaluate(broken)
    assert any(failure["type"] == "test_oracle_mismatch" for failure in failures)

    broken = deepcopy(reference)
    broken["result"]["nexus"] = None
    failures, _ = Evaluator(loaded).evaluate(broken)
    assert any(failure["type"] == "nexus_mismatch" for failure in failures)

    broken = deepcopy(reference)
    broken["classifications"] = []
    failures, _ = Evaluator(loaded).evaluate(broken)
    assert any(failure["type"] == "classification_keys" for failure in failures)


def test_evaluator_rejects_extra_decision_codes() -> None:
    loaded = scenario("01_basic_linear")
    reference = compute_reference(loaded)

    broken = deepcopy(reference)
    broken["stops_reviews"]["reviews"].append("REVIEW_99")
    failures, _ = Evaluator(loaded).evaluate(broken)
    assert any(failure["type"] == "reviews" for failure in failures)

    broken = deepcopy(reference)
    broken["stops_reviews"]["warnings"].append("WARNING_99")
    failures, _ = Evaluator(loaded).evaluate(broken)
    assert any(failure["type"] == "warnings" for failure in failures)


def test_test_key_space_alias_is_understood() -> None:
    loaded = scenario("01_basic_linear")
    reference = compute_reference(loaded)
    reference["tests"] = {key.replace("_", " "): value for key, value in reference["tests"].items()}
    failures, _ = Evaluator(loaded).evaluate(reference)
    assert failures == []


def test_invalid_scenario_contracts() -> None:
    loaded = load(SCENARIOS[0])
    for mutation in (
        lambda value: value.pop("meta"),
        lambda value: value["input"].pop("rok"),
        lambda value: value["input"].pop("forma_opodatkowania"),
        lambda value: value.update(assertions={}),
        lambda value: value["input"].pop("polityka_alokacji"),
    ):
        broken = deepcopy(loaded)
        mutation(broken)
        with pytest.raises(ScenarioError):
            validate_scenario(broken)


def test_runner_exposes_only_atomic_decision_facts() -> None:
    loaded = scenario("01_basic_linear")
    reference = compute_reference(loaded)
    context = build_tool_context(reference)
    assert context == {"decision_facts": reference["decision_facts"]}

    prompt = LLMTestRunner(None).build_prompt("ignored human documentation", loaded)
    assert "AUTORYTATYWNE FAKTY" in prompt
    assert "deterministic_report" not in prompt
    assert "result" not in prompt
    assert "decision_facts" in prompt
    assert "status, stops i reviews" in prompt


def test_decision_protocol_is_generated_from_code_maps() -> None:
    protocol = build_decision_protocol()
    assert "unsupported_tax_form=true -> STOP_01" in protocol
    assert "multiple_projects_or_ips=true -> REVIEW_04" in protocol
    assert "status=STOPPED" in protocol


def test_runner_assembles_deterministic_report_after_small_model_decision() -> None:
    loaded = scenario("45_multi_ip_two_stage")
    reference = compute_reference(loaded)
    runner = LLMTestRunner(None)
    raw_decision = yaml.safe_dump(decision_for(reference), sort_keys=False)
    # JSON is mandatory; YAML that is not JSON must be rejected.
    with pytest.raises(ValueError, match="pure JSON"):
        runner.validate_semantics(raw_decision, loaded)

    import json

    assembled = runner.validate_semantics(json.dumps(decision_for(reference)), loaded)
    assert assembled["result"] == reference["result"]
    assert assembled["tests"] == reference["tests"]
    assert assembled["stops_reviews"] == reference["stops_reviews"]


def test_runner_rejects_a_full_report_instead_of_decision_envelope() -> None:
    loaded = scenario("01_basic_linear")
    reference = compute_reference(loaded)
    runner = LLMTestRunner(None)

    import json

    with pytest.raises(ValueError, match="decision does not match strict schema"):
        runner.parse_decision(json.dumps(reference, ensure_ascii=False))


def test_oracle_stops_when_no_qualifying_ip_revenue() -> None:
    loaded = scenario("40_mixed_ip_clause")
    loaded = deepcopy(loaded)
    for client in loaded["input"]["kontrahenci"]:
        client["klauzula_IP"] = False
    for month in loaded["input"]["miesiace"]:
        for invoice in month["faktury"]:
            invoice["kwalifikuje_IP"] = False
    reference = compute_reference(loaded)
    assert reference["status"] == "STOPPED"
    assert reference["stops_reviews"]["stops"] == ["STOP_03"]
    assert reference["result"]["podatek"]["podatek_IP"] == 0
