from pathlib import Path
from typing import Any

import yaml

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_AI_SKILLS_REVISION = "1caa380151bdcf3285c9f9e59bdaf7b618e4bb16"


def _read(relative: str) -> str:
    return (_REPOSITORY_ROOT / relative).read_text(encoding="utf-8")


def _load_workflow(relative: str) -> dict[str, Any]:
    document = yaml.safe_load(_read(relative))
    assert isinstance(document, dict)
    return document


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
    matches = [(index, command) for index, command in enumerate(commands) if command.startswith(prefix)]
    assert len(matches) == 1
    return matches[0]


def test_deterministic_ci_runs_pinned_upstream_validators_outside_repository() -> None:
    workflow = _load_workflow(".github/workflows/deterministic-ci.yml")
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    deterministic = jobs.get("deterministic")
    assert isinstance(deterministic, dict)
    steps = deterministic.get("steps")
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) for step in steps)

    checkout = _named_step(steps, "Checkout pinned AI skills validators")
    checkout_with = checkout.get("with")
    assert isinstance(checkout_with, dict)
    assert checkout_with.get("repository") == "paulomac1000/ai-skills"
    assert checkout_with.get("ref") == _AI_SKILLS_REVISION
    assert checkout_with.get("path") == ".ai-skills-source"
    assert checkout_with.get("persist-credentials") is False

    validation = _named_step(steps, "Validate adopted AI skills")
    script = validation.get("run")
    assert isinstance(script, str)
    commands = _shell_commands(script)

    sha_check = (
        'test "$(git -C .ai-skills-source rev-parse HEAD)" = '
        f'"{_AI_SKILLS_REVISION}"'
    )
    assert sha_check in commands

    move_command = 'mv .ai-skills-source "$RUNNER_TEMP/ai-skills"'
    assignment = 'ai_skills="$RUNNER_TEMP/ai-skills"'
    assert move_command in commands
    assert assignment in commands

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

    move_index = commands.index(move_command)
    assignment_index = commands.index(assignment)
    assert move_index < assignment_index < audit_index < validate_index < afds_index

    for command in (audit, validate):
        assert "--strict" in command
        assert "--layout single" in command
        assert "--profile safety-critical" in command
        assert "--language pl" in command
    assert "--repository-root ." in validate
    assert validate.endswith("AGENTS.md 2>&1 | tee reports/agents-md-validation.txt")
    assert "docs/agent-development.md" in afds
    assert "docs/agent-tax-analysis.md" in afds
    assert "docs/decisions/ai-skills-adoption.md" in afds


def test_adoption_decision_and_dependencies_use_the_same_revision() -> None:
    decision = _read("docs/decisions/ai-skills-adoption.md")
    requirements = _read("requirements.txt")

    assert _AI_SKILLS_REVISION in decision
    assert "PyYAML==6.0.3" in requirements
    assert "requests==2.33.0" in requirements


def test_changelog_records_the_adoption_contract() -> None:
    changelog = _read("CHANGELOG.md")

    assert "### Instrukcje agentów, dokumentacja i bezpieczeństwo CI" in changelog
    assert "upstreamowe validatory" in changelog
