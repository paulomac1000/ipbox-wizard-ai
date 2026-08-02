"""Regression tests for the final eight-family cassette gate."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.llm.models import BENCHMARK_MODELS, MODEL_PROFILES, ModelProfile
from tests.llm.output_schema import DECISION_JSON_SCHEMA
from tests.llm.runner import LLMTestRunner

ROOT = Path(__file__).resolve().parents[2]
MODEL_SELECTION_GUARD = 'if [ "$BENCHMARK_MODEL" = "all" ]; then\n'


def _paid_workflow() -> dict:
    workflow_path = ROOT / ".github/workflows/llm-benchmark.yml"
    return yaml.safe_load(workflow_path.read_text(encoding="utf-8"))


def _bounded_shell_branches(script: str) -> tuple[str, str, str, str]:
    before_if, if_marker, conditional = script.partition(MODEL_SELECTION_GUARD)
    first_branch, else_marker, conditional = conditional.partition("\nelse\n")
    second_branch, fi_marker, after_fi = conditional.partition("\nfi")

    assert if_marker
    assert else_marker
    assert fi_marker
    return before_if, first_branch, second_branch, after_fi


def _logical_shell_commands(script: str) -> list[str]:
    commands: list[str] = []
    pending = ""

    for raw_line in script.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        pending = f"{pending} {line}".strip()
        if pending.endswith("\\"):
            pending = pending[:-1].rstrip()
            continue
        commands.append(pending)
        pending = ""

    if pending:
        commands.append(pending)
    return commands


def _step_script(name: str) -> str:
    steps = _paid_workflow()["jobs"]["benchmark"]["steps"]
    return next(step["run"] for step in steps if step.get("name") == name)


def _write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _stubbed_shell_environment(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    workspace = tmp_path / "workspace"
    fake_bin = tmp_path / "bin"
    command_log = tmp_path / "commands.log"
    workspace.mkdir(parents=True)
    fake_bin.mkdir(parents=True)

    _write_executable(
        fake_bin / "python",
        """#!/usr/bin/env bash
set -u
printf 'python %s\\n' "$*" >> "$COMMAND_LOG"
if [[ -n "${FAIL_COMMAND:-}" && "python $*" == *"$FAIL_COMMAND"* ]]; then
  exit "${FAIL_STATUS:-42}"
fi
exit 0
""",
    )
    for command in ("record_all_models.sh", "verify_all_models.sh"):
        _write_executable(
            workspace / "scripts" / command,
            f"""#!/usr/bin/env bash
set -u
printf '{command} %s\\n' "$*" >> "$COMMAND_LOG"
if [[ "${{FAIL_COMMAND:-}}" == "{command}" ]]; then
  exit "${{FAIL_STATUS:-42}}"
fi
exit 0
""",
        )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "COMMAND_LOG": str(command_log),
            "VCR_REJECTED_ROOT": str(tmp_path / "rejected"),
            "MAX_COST_PER_MODEL_USD": "1",
            "MAX_TOTAL_COST_USD": "2",
        }
    )
    return workspace, env, command_log


def _run_workflow_shell(
    script: str,
    workspace: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", script],
        cwd=workspace,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


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
    step_payloads = [json.dumps(step, sort_keys=True) for step in steps]
    non_run_step_payloads = [
        json.dumps(
            {key: value for key, value in step.items() if key != "run"},
            sort_keys=True,
        )
        for step in steps
    ]
    init_step = next(
        step for step in steps if step.get("name") == "Initialize isolated rejected-attempt path"
    )
    init_script = init_step["run"]

    assert "VCR_REJECTED_ROOT" not in job["env"]
    assert all("VCR_REJECTED_ROOT" not in payload for payload in non_run_step_payloads)

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
    init_exports = [
        line.strip() for line in init_script.splitlines() if "VCR_REJECTED_ROOT=" in line
    ]

    init_index = steps.index(init_step)
    consumer_indices = [
        index
        for index, payload in enumerate(step_payloads)
        if index != init_index and "VCR_REJECTED_ROOT" in payload
    ]

    assert init_script.count(expected_assignment) == 1
    assert init_exports == [expected_export]
    assert assignment_count == 1
    assert rejected_root_exports == [expected_export]
    assert consumer_indices
    assert init_index < min(consumer_indices)


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
    matrix_commands = _logical_shell_commands(matrix_script)
    assert matrix_script.count("python scripts/benchmark_report.py") == 1
    assert "trap generate_benchmark_report EXIT" in matrix_script
    assert "original_status=$?" in matrix_script
    assert "python scripts/benchmark_report.py || report_status=$?" in matrix_commands
    assert 'exit "$original_status"' in matrix_script
    assert 'exit "$report_status"' in matrix_script
    assert "|| true" not in matrix_script

    recorder_commands = ("scripts/record_all_models.sh", "scripts/record_model.py")
    for step in steps:
        if step is record_step:
            continue
        script = step.get("run", "")
        assert all(command not in script for command in recorder_commands)

    before_record_if, all_record_branch, single_record_branch, after_record_fi = (
        _bounded_shell_branches(record_step["run"])
    )
    before_record_commands = _logical_shell_commands(before_record_if)
    all_record_commands = _logical_shell_commands(all_record_branch)
    single_record_commands = _logical_shell_commands(single_record_branch)
    expected_all_recorder = " ".join(
        (
            "./scripts/record_all_models.sh",
            '--max-cost-per-model-usd "$MAX_COST_PER_MODEL_USD"',
            '--max-total-cost-usd "$MAX_TOTAL_COST_USD"',
        )
    )
    expected_single_recorder = " ".join(
        (
            "python scripts/record_model.py",
            '--model "$BENCHMARK_MODEL"',
            '--max-cost-per-model-usd "$MAX_COST_PER_MODEL_USD"',
            '--max-total-cost-usd "$MAX_TOTAL_COST_USD"',
        )
    )

    assert "set -euo pipefail" in before_record_commands
    assert "set +e" not in record_step["run"]
    for outside_branch in (before_record_if, after_record_fi):
        assert "record_all_models.sh" not in outside_branch
        assert "record_model.py" not in outside_branch
    assert all_record_commands.count(expected_all_recorder) == 1
    assert all("record_model.py" not in command for command in all_record_commands)
    assert single_record_commands.count(expected_single_recorder) == 1
    assert all("record_all_models.sh" not in command for command in single_record_commands)

    before_offline_if, all_offline_branch, single_offline_branch, after_offline_fi = (
        _bounded_shell_branches(offline_step["run"])
    )
    before_offline_commands = _logical_shell_commands(before_offline_if)
    single_offline_commands = _logical_shell_commands(single_offline_branch)
    single_model_report = 'python scripts/benchmark_report.py --model "$BENCHMARK_MODEL"'

    assert "set -euo pipefail" in before_offline_commands
    assert "set +e" not in offline_step["run"]
    assert "benchmark_report.py" not in before_offline_if
    assert "benchmark_report.py" not in all_offline_branch
    assert single_offline_commands.count(single_model_report) == 1
    assert "benchmark_report.py" not in after_offline_fi

    direct_workflow_report_count = sum(
        step.get("run", "").count("python scripts/benchmark_report.py") for step in steps
    )
    assert direct_workflow_report_count == 1

    upload_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Upload cassette candidates and reports"
    )
    record_index = steps.index(record_step)
    offline_index = steps.index(offline_step)
    assert record_index < offline_index < upload_index

    assert final_step is steps[-1]
    assert final_step["run"].count("python scripts/check_cassette_policy.py") == 1
    assert "benchmark_report.py" not in final_step["run"]


def test_paid_workflow_executes_only_the_selected_recorder(tmp_path: Path) -> None:
    script = _step_script("Record cassettes")

    workspace, env, command_log = _stubbed_shell_environment(tmp_path / "all")
    env["BENCHMARK_MODEL"] = "all"
    result = _run_workflow_shell(script, workspace, env)
    assert result.returncode == 0, result.stderr
    assert command_log.read_text(encoding="utf-8").splitlines() == [
        "record_all_models.sh --max-cost-per-model-usd 1 --max-total-cost-usd 2"
    ]

    workspace, env, command_log = _stubbed_shell_environment(tmp_path / "single")
    env["BENCHMARK_MODEL"] = "openai/gpt-5-mini"
    result = _run_workflow_shell(script, workspace, env)
    assert result.returncode == 0, result.stderr
    assert command_log.read_text(encoding="utf-8").splitlines() == [
        "python scripts/record_model.py --model openai/gpt-5-mini "
        "--max-cost-per-model-usd 1 --max-total-cost-usd 2"
    ]


@pytest.mark.parametrize(
    ("model", "failure"),
    [
        ("all", "record_all_models.sh"),
        ("openai/gpt-5-mini", "scripts/record_model.py"),
    ],
)
def test_paid_workflow_propagates_recorder_failures(
    tmp_path: Path,
    model: str,
    failure: str,
) -> None:
    workspace, env, _command_log = _stubbed_shell_environment(tmp_path)
    env.update(BENCHMARK_MODEL=model, FAIL_COMMAND=failure, FAIL_STATUS="43")

    result = _run_workflow_shell(_step_script("Record cassettes"), workspace, env)

    assert result.returncode == 43


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        (
            "all",
            [
                "verify_all_models.sh ",
                "python scripts/vcr_precommit.py --all-models",
                "python scripts/check_cassette_policy.py",
            ],
        ),
        (
            "openai/gpt-5-mini",
            [
                "python -m pytest tests/llm/test_scenarios.py --run-llm --vcr-mode=playback -q",
                "python scripts/vcr_precommit.py --model openai/gpt-5-mini",
                "python scripts/benchmark_report.py --model openai/gpt-5-mini",
            ],
        ),
    ],
)
def test_paid_workflow_runs_required_offline_verification_commands_in_order(
    tmp_path: Path,
    model: str,
    expected: list[str],
) -> None:
    workspace, env, command_log = _stubbed_shell_environment(tmp_path)
    env["BENCHMARK_MODEL"] = model
    env["OPENROUTER_API_KEY"] = "must-be-unset"

    result = _run_workflow_shell(_step_script("Offline verification (no API key)"), workspace, env)

    assert result.returncode == 0, result.stderr
    assert command_log.read_text(encoding="utf-8").splitlines() == expected


@pytest.mark.parametrize(
    ("model", "failure"),
    [
        ("all", "verify_all_models.sh"),
        ("all", "scripts/vcr_precommit.py"),
        ("all", "scripts/check_cassette_policy.py"),
        ("openai/gpt-5-mini", "-m pytest"),
        ("openai/gpt-5-mini", "scripts/vcr_precommit.py"),
        ("openai/gpt-5-mini", "scripts/benchmark_report.py"),
    ],
)
def test_paid_workflow_propagates_each_offline_verification_failure(
    tmp_path: Path,
    model: str,
    failure: str,
) -> None:
    workspace, env, _command_log = _stubbed_shell_environment(tmp_path)
    env.update(BENCHMARK_MODEL=model, FAIL_COMMAND=failure, FAIL_STATUS="44")

    result = _run_workflow_shell(_step_script("Offline verification (no API key)"), workspace, env)

    assert result.returncode == 44


@pytest.mark.parametrize(
    ("original_status", "report_status", "expected_status"),
    [(0, 0, 0), (7, 0, 7), (0, 9, 9), (7, 9, 7)],
)
def test_matrix_report_trap_preserves_original_and_report_failures(
    tmp_path: Path,
    original_status: int,
    report_status: int,
    expected_status: int,
) -> None:
    source = (ROOT / "scripts/record_all_models.sh").read_text(encoding="utf-8")
    start = source.index("generate_benchmark_report() {")
    end = source.index("\ntrap generate_benchmark_report EXIT", start)
    function = source[start:end]

    workspace, env, command_log = _stubbed_shell_environment(tmp_path)
    env.update(FAIL_COMMAND="scripts/benchmark_report.py", FAIL_STATUS=str(report_status))
    if report_status == 0:
        env.pop("FAIL_COMMAND")
    harness = f"""set -uo pipefail
{function}
trap generate_benchmark_report EXIT
exit {original_status}
"""

    result = _run_workflow_shell(harness, workspace, env)

    assert result.returncode == expected_status
    assert command_log.read_text(encoding="utf-8").splitlines() == [
        "python scripts/benchmark_report.py"
    ]


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
