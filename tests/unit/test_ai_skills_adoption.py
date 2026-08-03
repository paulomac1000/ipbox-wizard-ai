from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_AI_SKILLS_REVISION = "1caa380151bdcf3285c9f9e59bdaf7b618e4bb16"


def _read(relative: str) -> str:
    return (_REPOSITORY_ROOT / relative).read_text(encoding="utf-8")


def test_deterministic_ci_runs_pinned_upstream_validators_outside_repository() -> None:
    workflow = _read(".github/workflows/deterministic-ci.yml")

    assert f"ref: {_AI_SKILLS_REVISION}" in workflow
    assert 'test "$(git -C .ai-skills-source rev-parse HEAD)"' in workflow
    assert 'mv .ai-skills-source "$RUNNER_TEMP/ai-skills"' in workflow
    assert "skills/agents-md-architect/tools/audit_agents_md.py" in workflow
    assert "skills/agents-md-architect/tools/validate_agents_md.py" in workflow
    assert "skills/afds-doc-writer/validate.py" in workflow
    assert "--profile safety-critical" in workflow
    assert "--language pl" in workflow
    assert "--strict" in workflow


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
