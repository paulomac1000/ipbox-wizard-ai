#!/usr/bin/env python3
"""Validate GitHub Actions workflows from an untrusted repository tree."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

MAX_WORKFLOW_FILES = 128
MAX_WORKFLOW_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_DOCKER_DIGEST = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
_ACTION_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$")
_EXPRESSION_REFERENCE = re.compile(r"\$\{\{")
_SECRET_CONTEXT_REFERENCE = re.compile(
    r"\$\{\{(?:(?!\}\}).)*\bsecrets\b(?:(?!\}\}).)*\}\}",
    re.IGNORECASE | re.DOTALL,
)
_WRITE_PERMISSION = re.compile(r"(^|-)write$")
_WORKFLOW_SUFFIXES = {".yml", ".yaml"}
_MUTABLE_RUNNERS = {"ubuntu-latest", "windows-latest", "macos-latest"}


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class Finding:
    path: Path
    message: str

    def render(self) -> str:
        return f"{self.path.as_posix()}: {self.message}"


def _events(document: dict[Any, Any]) -> Any:
    """Return the workflow event declaration despite YAML 1.1 parsing `on` as bool."""
    return document.get("on", document.get(True))


def _event_names(events: Any) -> tuple[set[str], str | None]:
    if isinstance(events, str):
        return {events}, None
    if isinstance(events, dict):
        if not events:
            return set(), "workflow must declare events"
        if not all(isinstance(name, str) and name for name in events):
            return set(), "workflow event names must be non-empty strings"
        return set(events), None
    if isinstance(events, list):
        if not events:
            return set(), "workflow must declare events"
        if not all(isinstance(name, str) and name for name in events):
            return set(), "workflow event list must contain non-empty strings"
        return set(events), None
    if events is None:
        return set(), "workflow must declare events"
    return set(), "workflow events must be a string, list of strings, or mapping"


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _permission_findings(
    path: Path,
    permissions: Any,
    *,
    scope: str,
    allowed_read_scopes: frozenset[str] | None = None,
) -> list[Finding]:
    if permissions is None:
        return [Finding(path, f"{scope} must declare explicit permissions")]
    if not isinstance(permissions, dict):
        return [
            Finding(
                path,
                f"{scope} permissions must be an explicit mapping; shorthand values are forbidden",
            )
        ]

    findings: list[Finding] = []
    for name, access in permissions.items():
        if not isinstance(name, str) or not isinstance(access, str):
            findings.append(Finding(path, f"{scope} permission names and access values must be strings"))
            continue
        normalized_name = name.casefold()
        normalized_access = access.casefold()
        if _WRITE_PERMISSION.search(normalized_access):
            findings.append(
                Finding(
                    path,
                    f"{scope} grants {name}: {access}; this policy permits no write scope",
                )
            )
        elif normalized_access not in {"read", "none"}:
            findings.append(Finding(path, f"{scope} has unsupported permission {name}: {access}"))
        elif (
            normalized_access == "read"
            and allowed_read_scopes is not None
            and normalized_name not in allowed_read_scopes
        ):
            allowed = ", ".join(sorted(allowed_read_scopes)) or "none"
            findings.append(
                Finding(
                    path,
                    f"{scope} grants {name}: read; allowed read scopes are: {allowed}",
                )
            )
    return findings


def _external_action_findings(path: Path, label: str, uses: Any) -> list[Finding]:
    if not isinstance(uses, str):
        return [Finding(path, f"{label} has non-string uses value")]
    if uses.startswith("./"):
        return []
    if uses.startswith("docker://"):
        image = uses.removeprefix("docker://")
        if not _DOCKER_DIGEST.fullmatch(image):
            return [
                Finding(
                    path,
                    f"{label} Docker action must use an exact sha256 digest",
                )
            ]
        return []
    if "@" not in uses:
        return [Finding(path, f"{label} action {uses!r} has no immutable revision")]

    action, revision = uses.rsplit("@", 1)
    findings: list[Finding] = []
    if not _ACTION_NAME.fullmatch(action):
        findings.append(Finding(path, f"{label} action {action!r} has invalid owner/repository syntax"))
    if not _FULL_SHA.fullmatch(revision):
        findings.append(Finding(path, f"{label} action {action!r} must use a full 40-character SHA"))
    return findings


def _action_findings(
    path: Path,
    job_name: str,
    step_index: int,
    step: Any,
) -> list[Finding]:
    if not isinstance(step, dict) or "uses" not in step:
        return []

    uses = step["uses"]
    label = f"job {job_name!r} step {step_index}"
    findings = _external_action_findings(path, label, uses)
    if not isinstance(uses, str):
        return findings

    action = uses.rsplit("@", 1)[0]
    with_block = step.get("with")
    if action == "actions/checkout" and (
        not isinstance(with_block, dict) or with_block.get("persist-credentials") is not False
    ):
        findings.append(Finding(path, f"{label} actions/checkout must set persist-credentials: false"))

    if action == "actions/upload-artifact":
        if not isinstance(with_block, dict):
            findings.append(Finding(path, f"{label} upload-artifact requires a with mapping"))
        else:
            if not _positive_int(with_block.get("retention-days")):
                findings.append(Finding(path, f"{label} upload-artifact needs positive retention-days"))
            if with_block.get("if-no-files-found") not in {"error", "warn", "ignore"}:
                findings.append(
                    Finding(
                        path,
                        f"{label} upload-artifact needs explicit if-no-files-found",
                    )
                )

    return findings


def _runner_findings(path: Path, job_name: str, runs_on: Any) -> list[Finding]:
    scope = f"job {job_name!r}"
    if not isinstance(runs_on, str) or not runs_on.strip():
        return [Finding(path, f"{scope} runs-on must be a non-empty literal string")]
    normalized_runs_on = runs_on.strip()
    if _EXPRESSION_REFERENCE.search(normalized_runs_on):
        return [
            Finding(
                path,
                f"{scope} runs-on expressions are forbidden; pin a concrete runner",
            )
        ]
    if normalized_runs_on.casefold() in _MUTABLE_RUNNERS:
        return [Finding(path, f"{scope} must pin a concrete runner instead of {runs_on}")]
    return []


def _scalar_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _scalar_strings(key)
            yield from _scalar_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _scalar_strings(item)


WorkflowReader = Callable[[Path, Path], tuple[str | None, str | None]]
WorkflowEnumerator = Callable[[Path], tuple[list[Path], list[Finding]]]


def audit_workflow(
    path: Path,
    repository_root: Path,
    *,
    reader: WorkflowReader,
) -> list[Finding]:
    root = repository_root.resolve()
    raw_text, read_error = reader(path, root)
    if read_error is not None:
        return [Finding(path, read_error)]
    assert raw_text is not None

    try:
        document = yaml.load(raw_text, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        return [Finding(path, f"cannot parse workflow: {exc}")]

    if not isinstance(document, dict):
        return [Finding(path, "workflow root must be a mapping")]

    findings: list[Finding] = []
    event_names, event_error = _event_names(_events(document))
    if event_error:
        findings.append(Finding(path, event_error))
    if "pull_request_target" in event_names:
        findings.append(Finding(path, "pull_request_target is forbidden for repository code"))

    pull_request_workflow = "pull_request" in event_names
    allowed_read_scopes = frozenset({"contents"}) if pull_request_workflow else None
    findings.extend(
        _permission_findings(
            path,
            document.get("permissions"),
            scope="workflow",
            allowed_read_scopes=allowed_read_scopes,
        )
    )

    concurrency = document.get("concurrency")
    if not isinstance(concurrency, dict):
        findings.append(Finding(path, "workflow must declare concurrency as a mapping"))
    else:
        group = concurrency.get("group")
        if not isinstance(group, str) or not group.strip():
            findings.append(Finding(path, "workflow must declare a non-empty concurrency group"))
        if not isinstance(concurrency.get("cancel-in-progress"), bool):
            findings.append(Finding(path, "concurrency cancel-in-progress must be a boolean"))

    jobs = document.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        return [*findings, Finding(path, "workflow must declare at least one job")]

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            findings.append(Finding(path, f"job {job_name!r} must be a mapping"))
            continue
        if "uses" in job:
            findings.append(Finding(path, f"job {job_name!r} reusable workflow calls are not supported"))
            findings.extend(_external_action_findings(path, f"job {job_name!r}", job.get("uses")))
            continue

        if not _positive_int(job.get("timeout-minutes")):
            findings.append(Finding(path, f"job {job_name!r} needs positive timeout-minutes"))
        findings.extend(_runner_findings(path, str(job_name), job.get("runs-on")))
        if "permissions" in job:
            findings.extend(
                _permission_findings(
                    path,
                    job.get("permissions"),
                    scope=f"job {job_name!r}",
                    allowed_read_scopes=allowed_read_scopes,
                )
            )

        steps = job.get("steps", [])
        if not isinstance(steps, list):
            findings.append(Finding(path, f"job {job_name!r} steps must be a list"))
            continue
        for index, step in enumerate(steps, start=1):
            findings.extend(_action_findings(path, str(job_name), index, step))

    if pull_request_workflow and any(_SECRET_CONTEXT_REFERENCE.search(value) for value in _scalar_strings(document)):
        findings.append(Finding(path, "pull-request workflows must not reference repository secrets"))

    return findings


def audit_repository(
    repository_root: Path,
    *,
    reader: WorkflowReader,
    enumerator: WorkflowEnumerator,
) -> list[Finding]:
    root = repository_root.resolve()
    paths, findings = enumerator(root)
    if not paths and not findings:
        findings.append(Finding(root, "no GitHub Actions workflows found"))
    for path in paths:
        findings.extend(audit_workflow(path, root, reader=reader))
    return findings
