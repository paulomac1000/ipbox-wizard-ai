import sys
from pathlib import Path

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPOSITORY_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from check_workflow_policy import (  # noqa: E402
    audit_repository,
    audit_workflow,
    read_utf8_bounded,
)

confined_io = sys.modules["confined_io"]


def _messages(workflow: Path) -> list[str]:
    return [finding.message for finding in audit_workflow(workflow)]


def test_local_launcher_uses_vendored_confined_reader() -> None:
    assert read_utf8_bounded is confined_io.read_utf8_bounded
    assert (
        Path(confined_io.__file__).resolve()
        == (_REPOSITORY_ROOT / "vendor" / "ai-skills" / "contracts" / "confined_io.py").resolve()
    )


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


@pytest.mark.parametrize("permissions", ("read-all", "none"))
def test_policy_rejects_permission_shorthands(
    tmp_path: Path,
    permissions: str,
) -> None:
    workflow = tmp_path / "permissions.yml"
    workflow.write_text(
        f"""
name: permissions
on: workflow_dispatch
permissions: {permissions}
concurrency:
  group: permissions
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

    messages = _messages(workflow)
    assert any("must be an explicit mapping" in message for message in messages)


def test_policy_accepts_empty_permission_mapping(tmp_path: Path) -> None:
    workflow = tmp_path / "no-permissions.yml"
    workflow.write_text(
        """
name: no-permissions
on: workflow_dispatch
permissions: {}
concurrency:
  group: no-permissions
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

    assert _messages(workflow) == []


def test_policy_rejects_additional_read_scopes_in_pull_request_workflows(
    tmp_path: Path,
) -> None:
    workflow = tmp_path / "pr-permissions.yml"
    workflow.write_text(
        """
name: pr-permissions
on: pull_request
permissions:
  contents: read
  actions: read
concurrency:
  group: pr-permissions
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    permissions:
      contents: read
      packages: read
    steps:
      - run: echo test
""".lstrip(),
        encoding="utf-8",
    )

    messages = _messages(workflow)
    assert any("workflow grants actions: read" in message for message in messages)
    assert any("job 'test' grants packages: read" in message for message in messages)


@pytest.mark.parametrize(
    "secret_reference",
    (
        "${{ secrets.SOME_TOKEN }}",
        "${{ secrets['SOME_TOKEN'] }}",
        '${{ secrets["SOME_TOKEN"] }}',
        "${{ toJSON(secrets) }}",
    ),
)
def test_policy_rejects_secret_in_pull_request_workflow(
    tmp_path: Path,
    secret_reference: str,
) -> None:
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
      TOKEN: SECRET_REFERENCE
    steps:
      - run: echo test
""".lstrip().replace("SECRET_REFERENCE", secret_reference),
        encoding="utf-8",
    )

    messages = _messages(workflow)
    assert any("must not reference repository secrets" in message for message in messages)


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


@pytest.mark.parametrize("event_declaration", ("{}", "[]"))
def test_policy_rejects_empty_event_declaration(
    tmp_path: Path,
    event_declaration: str,
) -> None:
    workflow = tmp_path / "empty-events.yml"
    workflow.write_text(
        f"""
name: empty-events
on: {event_declaration}
permissions:
  contents: read
concurrency:
  group: empty-events
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

    assert any("must declare events" in message for message in _messages(workflow))


@pytest.mark.parametrize(
    ("runs_on", "expected_message"),
    (
        ("[ubuntu-latest]", "non-empty literal string"),
        ("${{ matrix.os }}", "runs-on expressions are forbidden"),
    ),
)
def test_policy_rejects_nonliteral_runner_values(
    tmp_path: Path,
    runs_on: str,
    expected_message: str,
) -> None:
    workflow = tmp_path / "runner.yml"
    workflow.write_text(
        f"""
name: runner
on: workflow_dispatch
permissions:
  contents: read
concurrency:
  group: runner
  cancel-in-progress: true
jobs:
  test:
    runs-on: {runs_on}
    timeout-minutes: 10
    steps:
      - run: echo test
""".lstrip(),
        encoding="utf-8",
    )

    assert any(expected_message in message for message in _messages(workflow))


@pytest.mark.parametrize(
    "uses",
    (
        "docker://alpine:3.20",
        "docker://alpine@sha256:not-a-digest",
    ),
)
def test_policy_rejects_mutable_or_malformed_docker_action(
    tmp_path: Path,
    uses: str,
) -> None:
    workflow = tmp_path / "docker.yml"
    workflow.write_text(
        f"""
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
      - uses: {uses}
""".lstrip(),
        encoding="utf-8",
    )

    messages = _messages(workflow)
    assert any("exact sha256 digest" in message for message in messages)


def test_policy_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    workflow = tmp_path / "duplicate.yml"
    workflow.write_text(
        """
name: duplicate
on: workflow_dispatch
permissions:
  contents: read
permissions:
  contents: write
concurrency:
  group: duplicate
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

    assert any("duplicate key" in message for message in _messages(workflow))
