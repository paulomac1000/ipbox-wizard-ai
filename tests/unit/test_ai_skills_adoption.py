from pathlib import Path
from typing import Any

import yaml

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_AI_SKILLS_REVISION = "9757a0b19803731d6974b797092032a0b0739a46"


def _read(relative: str) -> str:
    return (_REPOSITORY_ROOT / relative).read_text(encoding="utf-8")


def _load_workflow(relative: str) -> dict[str, Any]:
    document = yaml.safe_load(_read(relative))
    assert isinstance(document, dict)
    return document


def _job_steps(workflow: dict[str, Any], job_name: str) -> list[dict[str, Any]]:
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    job = jobs.get(job_name)
    assert isinstance(job, dict)
    steps = job.get("steps")
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) for step in steps)
    return steps


def _active_requirement_lines(text: str) -> set[str]:
    return {
        line.split("#", 1)[0].strip() for line in text.splitlines() if line.split("#", 1)[0].strip()
    }


def _shell_commands(script: str) -> list[str]:
    commands: list[str] = []
    current = ""
    for raw_line in script.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        current = f"{current} {line}".strip()
        if current.endswith("\\"):
            current = current[:-1].rstrip()
            continue
        commands.append(current)
        current = ""
    if current:
        commands.append(current)
    return commands


def _named_step(steps: list[dict[str, Any]], name: str) -> dict[str, Any]:
    matches = [step for step in steps if step.get("name") == name]
    assert len(matches) == 1
    return matches[0]


def _command_with_prefix(commands: list[str], prefix: str) -> tuple[int, str]:
    matches = [
        (index, command) for index, command in enumerate(commands) if command.startswith(prefix)
    ]
    assert len(matches) == 1
    return matches[0]


def _checkout_assertions(step: dict[str, Any]) -> None:
    checkout_with = step.get("with")
    assert isinstance(checkout_with, dict)
    assert checkout_with.get("repository") == "paulomac1000/ai-skills"
    assert checkout_with.get("ref") == _AI_SKILLS_REVISION
    assert checkout_with.get("path") == ".ai-skills-source"
    assert checkout_with.get("persist-credentials") is False


def _policy_mirror_assertions(commands: list[str], policy_root: str) -> int:
    policy_assignment = (
        f'workflow_policy="{policy_root}/skills/ci-cd-architect/tools/'
        'check_github_actions_policy.py"'
    )
    implementation_assignment = (
        f'workflow_policy_impl="{policy_root}/skills/ci-cd-architect/tools/'
        'check_github_actions_policy_impl.py"'
    )
    wrapper_check = 'cmp scripts/check_workflow_policy.py "$workflow_policy"'
    implementation_check = (
        'cmp scripts/check_github_actions_policy_impl.py "$workflow_policy_impl"'
    )
    policy_index, _ = _command_with_prefix(commands, 'python "$workflow_policy" .')

    for command in (
        policy_assignment,
        implementation_assignment,
        wrapper_check,
        implementation_check,
    ):
        assert command in commands
    assert (
        commands.index(policy_assignment)
        < commands.index(implementation_assignment)
        < commands.index(wrapper_check)
        < commands.index(implementation_check)
        < policy_index
    )
    return policy_index


def test_deterministic_ci_runs_pinned_upstream_validators_outside_repository() -> None:
    workflow = _load_workflow(".github/workflows/deterministic-ci.yml")
    steps = _job_steps(workflow, "deterministic")

    _checkout_assertions(_named_step(steps, "Checkout pinned AI skills validators"))

    validation = _named_step(steps, "Validate adopted AI skills")
    script = validation.get("run")
    assert isinstance(script, str)
    commands = _shell_commands(script)

    sha_check = f'test "$(git -C .ai-skills-source rev-parse HEAD)" = "{_AI_SKILLS_REVISION}"'
    move_command = 'mv .ai-skills-source "$RUNNER_TEMP/ai-skills"'
    assignment = 'ai_skills="$RUNNER_TEMP/ai-skills"'
    policy_index = _policy_mirror_assertions(commands, "$ai_skills")
    audit_index, audit = _command_with_prefix(
        commands,
        'python "$ai_skills/skills/agents-md-architect/tools/audit_agents_md.py"',
    )
    validate_index, validate = _command_with_prefix(
        commands,
        'python "$ai_skills/skills/agents-md-architect/tools/validate_agents_md.py"',
    )
    afds_index, afds = _command_with_prefix(
        commands,
        'python "$ai_skills/skills/afds-doc-writer/validate.py"',
    )

    assert sha_check in commands
    assert move_command in commands
    assert assignment in commands

    move_index = commands.index(move_command)
    assignment_index = commands.index(assignment)
    assert move_index < assignment_index < policy_index < audit_index < validate_index < afds_index

    policy = commands[policy_index]
    assert policy.endswith("2>&1 | tee reports/workflow-policy.txt")
    for command in (audit, validate):
        assert "--strict" in command
        assert "--layout single" in command
        assert "--profile safety-critical" in command
        assert "--language pl" in command
    assert "--repository-root ." in validate
    assert validate.endswith("AGENTS.md 2>&1 | tee reports/agents-md-validation.txt")
    assert "docs/agent-development.md" in afds
    assert "docs/agent-tax-analysis.md" in afds
    assert "docs/decisions/" not in afds

    run_scripts = "\n".join(
        str(step.get("run", "")) for step in steps if isinstance(step.get("run", ""), str)
    )
    assert "python scripts/check_workflow_policy.py" not in run_scripts
    assert not any(step.get("name") == "Validate workflow policy" for step in steps)


def test_paid_benchmark_uses_trusted_policy_and_scopes_secret_to_paid_steps() -> None:
    workflow = _load_workflow(".github/workflows/llm-benchmark.yml")
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    benchmark = jobs.get("benchmark")
    assert isinstance(benchmark, dict)
    job_env = benchmark.get("env")
    assert isinstance(job_env, dict)
    assert "OPENROUTER_API_KEY" not in job_env

    steps = _job_steps(workflow, "benchmark")
    _checkout_assertions(_named_step(steps, "Checkout pinned AI skills policy auditor"))

    trusted = _named_step(steps, "Validate trusted workflow policy")
    script = trusted.get("run")
    assert isinstance(script, str)
    commands = _shell_commands(script)
    sha_check = f'test "$(git -C .ai-skills-source rev-parse HEAD)" = "{_AI_SKILLS_REVISION}"'
    move_command = 'mv .ai-skills-source "$RUNNER_TEMP/ai-skills"'
    policy_index = _policy_mirror_assertions(commands, "$RUNNER_TEMP/ai-skills")
    assert sha_check in commands
    assert move_command in commands
    assert commands.index(move_command) < policy_index

    secret_steps: set[str] = set()
    for step in steps:
        env = step.get("env")
        if not isinstance(env, dict) or "OPENROUTER_API_KEY" not in env:
            continue
        name = step.get("name")
        assert isinstance(name, str)
        assert env["OPENROUTER_API_KEY"] == "${{ secrets.OPENROUTER_API_KEY }}"
        secret_steps.add(name)
    assert secret_steps == {"Validate API key and cost guards", "Record cassettes"}

    step_names = [step.get("name") for step in steps]
    assert step_names.index("Validate trusted workflow policy") < step_names.index(
        "Validate API key and cost guards"
    )
    assert step_names.index("Deterministic gates before paid calls") < step_names.index(
        "Record cassettes"
    )


def test_dependencies_match_upstream_runtime_contract_without_decision_document() -> None:
    active_requirements = _active_requirement_lines(_read("requirements.txt"))

    assert "PyYAML==6.0.3" in active_requirements
    assert "requests==2.33.0" in active_requirements
    assert not (_REPOSITORY_ROOT / "docs/decisions/ai-skills-adoption.md").exists()


def test_makefile_remains_the_canonical_full_quality_gate() -> None:
    readme = _read("README.md")
    testing = _read("docs/testing.md")
    makefile = _read("Makefile")
    pyproject = _read("pyproject.toml")

    assert "full: test verify" in makefile
    assert "`Makefile` jest kanonicznym właścicielem" in readme
    assert "`Makefile` jest kanonicznym właścicielem" in testing
    assert "make full" in readme
    assert "make full" in testing
    assert "ruff format --check ." not in readme
    assert "ruff format --check ." not in testing
    assert '"scripts/check_workflow_policy.py"' in pyproject
    assert '"scripts/check_github_actions_policy_impl.py"' in pyproject


def test_windows_full_gate_creates_the_environment_inside_wsl() -> None:
    readme = _read("README.md")
    windows = readme.split("### Windows — WSL", 1)[1].split("### macOS i Linux", 1)[0]

    assert "Czysty PowerShell" in windows
    assert "GNU Make" in windows
    assert "Bash" in windows
    assert "WSL" in windows
    assert "Activate.ps1" not in windows

    venv_index = windows.index("python3 -m venv .venv")
    activation_index = windows.index("source .venv/bin/activate")
    install_index = windows.index(
        "python -m pip install -r requirements.txt -r requirements-test.txt"
    )
    gate_index = windows.index("make full")
    assert venv_index < activation_index < install_index < gate_index


def test_changelog_records_the_adoption_contract() -> None:
    changelog = _read("CHANGELOG.md")

    assert "### Instrukcje agentów, dokumentacja i bezpieczeństwo CI" in changelog
    assert "upstreamowe validatory" in changelog
    assert "zewnętrznej, przypiętej rewizji" in changelog
    assert "sekret płatnego benchmarku" in changelog.casefold()
