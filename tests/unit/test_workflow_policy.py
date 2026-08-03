from pathlib import Path

from scripts.check_workflow_policy import audit_repository, audit_workflow


def test_repository_workflows_follow_policy() -> None:
    assert audit_repository(Path.cwd()) == []


def test_policy_rejects_mutable_action_write_permission_and_missing_timeout(
    tmp_path: Path,
) -> None:
    workflow = tmp_path / "unsafe.yml"
    workflow.write_text(
        """
name: unsafe
on: [pull_request]
permissions:
  contents: write
concurrency:
  group: unsafe
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
""".lstrip(),
        encoding="utf-8",
    )

    messages = [finding.message for finding in audit_workflow(workflow)]

    assert any("contents: write" in message for message in messages)
    assert any("positive timeout-minutes" in message for message in messages)
    assert any("full 40-character SHA" in message for message in messages)
    assert any("persist-credentials: false" in message for message in messages)
