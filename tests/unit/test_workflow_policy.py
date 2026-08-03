from pathlib import Path

from scripts.check_workflow_policy import audit_repository, audit_workflow

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _messages(workflow: Path) -> list[str]:
    return [finding.message for finding in audit_workflow(workflow)]


def test_repository_workflows_follow_policy() -> None:
    assert audit_repository(_REPOSITORY_ROOT) == []


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

    messages = _messages(workflow)

    assert any("contents: write" in message for message in messages)
    assert any("positive timeout-minutes" in message for message in messages)
    assert any("full 40-character SHA" in message for message in messages)
    assert any("persist-credentials: false" in message for message in messages)
    assert any("pin a concrete runner" in message for message in messages)


def test_policy_rejects_secret_in_pull_request_workflow(tmp_path: Path) -> None:
    workflow = tmp_path / "secret.yml"
    workflow.write_text(
        """
name: secret
on: pull_request
permissions:
  contents: read
concurrency:
  group: secret
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    env:
      TOKEN: ${{ secrets.SOME_TOKEN }}
    steps:
      - run: echo test
""".lstrip(),
        encoding="utf-8",
    )

    assert any("must not reference repository secrets" in message for message in _messages(workflow))


def test_policy_reports_invalid_event_shape_without_crashing(tmp_path: Path) -> None:
    workflow = tmp_path / "events.yml"
    workflow.write_text(
        """
name: events
on: true
permissions:
  contents: read
concurrency:
  group: events
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
      - run: echo test
""".lstrip(),
        encoding="utf-8",
    )

    assert any("events must be" in message for message in _messages(workflow))


def test_policy_rejects_mutable_docker_action(tmp_path: Path) -> None:
    workflow = tmp_path / "docker.yml"
    workflow.write_text(
        """
name: docker
on: workflow_dispatch
permissions:
  contents: read
concurrency:
  group: docker
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
      - uses: docker://alpine:3.20
""".lstrip(),
        encoding="utf-8",
    )

    assert any("immutable sha256 digest" in message for message in _messages(workflow))
