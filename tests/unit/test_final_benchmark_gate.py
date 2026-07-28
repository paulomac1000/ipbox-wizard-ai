"""Regression tests for the final eight-family cassette gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tests.llm.models import BENCHMARK_MODELS, MODEL_PROFILES, ModelProfile
from tests.llm.output_schema import DECISION_JSON_SCHEMA
from tests.llm.runner import LLMTestRunner

ROOT = Path(__file__).resolve().parents[2]


def _paid_workflow() -> dict:
    workflow_path = ROOT / ".github/workflows/llm-benchmark.yml"
    return yaml.safe_load(workflow_path.read_text(encoding="utf-8"))


def test_release_gate_contains_exactly_eight_distinct_model_families() -> None:
    assert len(BENCHMARK_MODELS) == 8
    assert len({MODEL_PROFILES[model].family for model in BENCHMARK_MODELS}) == 8
    assert "openai/gpt-5-mini" in BENCHMARK_MODELS
    assert "openai/gpt-5-nano" not in MODEL_PROFILES
    assert "z-ai/glm-4.7-flash" not in MODEL_PROFILES


def test_paid_workflow_model_allowlist_matches_canonical_registry() -> None:
    workflow = _paid_workflow()

    # PyYAML 1.1 may parse the plain scalar `on` as the boolean True.
    trigger = workflow.get("on", workflow.get(True))
    options = trigger["workflow_dispatch"]["inputs"]["model"]["options"]

    assert options == ["all", *BENCHMARK_MODELS]


def test_paid_workflow_initializes_exactly_one_rejected_root_at_runtime() -> None:
    workflow = _paid_workflow()
    job = workflow["jobs"]["benchmark"]
    steps = job["steps"]
    run_scripts = [step.get("run", "") for step in steps]
    init_step = next(
        step for step in steps if step.get("name") == "Initialize isolated rejected-attempt path"
    )
    record_step = next(step for step in steps if step.get("name") == "Record cassettes")

    assert "VCR_REJECTED_ROOT" not in job["env"]

    expected_assignment = "".join(
        ("rejected_root=", '"$RUNNER_TEMP/', 'ipbox_llm_rejected_${GITHUB_RUN_ID}"')
    )
    expected_export = " ".join(
        ("printf", "'VCR_REJECTED_ROOT=%s\\n'", '"$rejected_root"', ">>", '"$GITHUB_ENV"')
    )
    assignment_count = sum(script.count(expected_assignment) for script in run_scripts)
    rejected_root_exports = [
        line.strip()
        for script in run_scripts
        for line in script.splitlines()
        if "VCR_REJECTED_ROOT=" in line
    ]

    assert assignment_count == 1
    assert rejected_root_exports == [expected_export]
    assert steps.index(init_step) < steps.index(record_step)


def test_all_model_workflow_generates_one_report_before_artifact_upload() -> None:
    workflow = _paid_workflow()
    steps = workflow["jobs"]["benchmark"]["steps"]
    record_step = next(step for step in steps if step.get("name") == "Record cassettes")
    offline_step = next(
        step for step in steps if step.get("name") == "Offline verification (no API key)"
    )
    final_step = next(
        step for step in steps if step.get("name") == "Require a complete matrix for all-model runs"
    )

    matrix_script = (ROOT / "scripts/record_all_models.sh").read_text(encoding="utf-8")
    assert matrix_script.count("python scripts/benchmark_report.py") == 1
    assert "trap generate_benchmark_report EXIT" in matrix_script
    assert "original_status=$?" in matrix_script
    assert 'exit "$original_status"' in matrix_script
    assert 'exit "$report_status"' in matrix_script

    record_run = record_step["run"]
    before_if, if_marker, conditional = record_run.partition(
        'if [ "$BENCHMARK_MODEL" = "all" ]; then\n'
    )
    all_record_branch, else_marker, conditional = conditional.partition("\nelse\n")
    single_record_branch, fi_marker, after_fi = conditional.partition("\nfi")

    assert if_marker
    assert else_marker
    assert fi_marker
    for outside_branch in (before_if, after_fi):
        assert "record_all_models.sh" not in outside_branch
        assert "record_model.py" not in outside_branch
    assert all_record_branch.count("./scripts/record_all_models.sh") == 1
    assert "record_model.py" not in all_record_branch
    assert single_record_branch.count("python scripts/record_model.py") == 1
    assert "record_all_models.sh" not in single_record_branch

    offline_run = offline_step["run"]
    all_model_branch, single_model_branch = offline_run.split("else", maxsplit=1)
    single_model_report = 'python scripts/benchmark_report.py --model "$BENCHMARK_MODEL"'
    assert "benchmark_report.py" not in all_model_branch
    assert single_model_branch.count(single_model_report) == 1

    direct_workflow_report_count = sum(
        step.get("run", "").count("python scripts/benchmark_report.py") for step in steps
    )
    assert direct_workflow_report_count == 1

    upload_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Upload cassette candidates and reports"
    )
    assert steps.index(record_step) < upload_index

    assert final_step is steps[-1]
    assert final_step["run"].count("python scripts/check_cassette_policy.py") == 1
    assert "benchmark_report.py" not in final_step["run"]


def test_provider_transport_profiles_are_explicit_and_validated() -> None:
    claude = MODEL_PROFILES["anthropic/claude-haiku-4.5"]
    minimax = MODEL_PROFILES["minimax/minimax-m2.5"]
    openai = MODEL_PROFILES["openai/gpt-5-mini"]

    assert claude.response_format_type == "json_schema"
    assert claude.strip_unique_items_for_transport is True
    assert minimax.response_format_type == "json_object"
    assert minimax.strip_unique_items_for_transport is False
    assert openai.response_format_type == "json_schema"
    assert openai.reasoning == {"effort": "minimal"}
    assert openai.temperature is None

    with pytest.raises(ValueError, match="response_format_type"):
        ModelProfile(model_id="x", label="x", family="x", response_format_type="invalid")
    with pytest.raises(ValueError, match="valid only with json_schema"):
        ModelProfile(
            model_id="x",
            label="x",
            family="x",
            response_format_type="json_object",
            strip_unique_items_for_transport=True,
        )


def test_transport_schema_compatibility_never_weakens_local_validation() -> None:
    local_schema = DECISION_JSON_SCHEMA["schema"]
    assert local_schema["properties"]["stops"]["uniqueItems"] is True
    assert local_schema["properties"]["reviews"]["uniqueItems"] is True

    transport = LLMTestRunner._transport_schema(strip_unique=True)
    transport_properties = transport["schema"]["properties"]
    assert "uniqueItems" not in transport_properties["stops"]
    assert "uniqueItems" not in transport_properties["reviews"]

    # Building a provider-compatible copy must never mutate the local source of truth.
    assert local_schema["properties"]["stops"]["uniqueItems"] is True
    assert local_schema["properties"]["reviews"]["uniqueItems"] is True

    nested = {"uniqueItems": True, "items": [{"properties": {"x": {"uniqueItems": True}}}]}
    LLMTestRunner._remove_schema_keyword(nested, "uniqueItems")
    assert nested == {"items": [{"properties": {"x": {}}}]}


def test_authoritative_contract_documents_match_the_executable_protocol() -> None:
    for relative_path in (
        "ipbox_algorytm.md",
        ".agents/onboarding.md",
        "examples/przykladowy_prompt_startowy.md",
    ):
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "expected_decision" in text, relative_path
        assert "active_rules" not in text, relative_path


def test_runner_rejects_review_codes_routed_to_stops_at_schema_boundary() -> None:
    runner = LLMTestRunner(client=None)
    payload = json.dumps(
        {
            "status": "STOPPED",
            "stops": ["REVIEW_01", "REVIEW_09"],
            "reviews": [],
        }
    )

    with pytest.raises(ValueError, match="decision does not match strict schema"):
        runner.parse_decision(payload)


def test_runner_rejects_status_inconsistent_with_stop_presence() -> None:
    runner = LLMTestRunner(client=None)
    payload = json.dumps(
        {
            "status": "STOPPED",
            "stops": [],
            "reviews": ["REVIEW_01"],
        }
    )

    with pytest.raises(ValueError, match="inconsistent with stops"):
        runner.parse_decision(payload)
