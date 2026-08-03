"""Validate repository-specific GitHub Actions security and reliability policy."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_SECRET_REFERENCE = re.compile(r"\$\{\{\s*secrets\.", re.IGNORECASE)
_WRITE_PERMISSION = re.compile(r"(^|-)write$")
_WORKFLOW_SUFFIXES = {".yml", ".yaml"}
_MUTABLE_RUNNERS = {"ubuntu-latest", "windows-latest", "macos-latest"}


@dataclass(frozen=True)
class Finding:
    path: Path
    message: str

    def render(self) -> str:
        return f"{self.path.as_posix()}: {self.message}"


def _events(document: dict[str, Any]) -> Any:
    """Return the workflow event declaration despite YAML 1.1 parsing `on` as bool."""
    return document.get("on", document.get(True))


def _event_names(events: Any) -> tuple[set[str], str | None]:
    if isinstance(events, str):
        return {events}, None
    if isinstance(events, dict):
        return {str(name) for name in events}, None
    if isinstance(events, list) and all(isinstance(name, str) for name in events):
        return set(events), None
    if events is None:
        return set(), "workflow must declare events"
    return set(), "workflow events must be a string, list of strings, or mapping"


def _is_false(value: Any) -> bool:
    return value is False or (isinstance(value, str) and value.lower() == "false")


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _permission_findings(
    path: Path,
    permissions: Any,
    *,
    scope: str,
) -> list[Finding]:
    findings: list[Finding] = []
    if permissions is None:
        return [Finding(path, f"{scope} must declare explicit permissions")]
    if isinstance(permissions, str):
        if permissions not in {"read-all", "none"}:
            findings.append(
                Finding(path, f"{scope} uses unsupported permissions value {permissions!r}")
            )
        return findings
    if not isinstance(permissions, dict):
        return [Finding(path, f"{scope} permissions must be a mapping or read-all/none")]

    for name, access in permissions.items():
        normalized = str(access).lower()
        if _WRITE_PERMISSION.search(normalized):
            findings.append(
                Finding(path, f"{scope} grants {name}: {access}; this repository has no write job")
            )
        elif normalized not in {"read", "none"}:
            findings.append(Finding(path, f"{scope} has unsupported permission {name}: {access}"))
    return findings


def _external_action_finding(path: Path, label: str, uses: Any) -> list[Finding]:
    if not isinstance(uses, str):
        return [Finding(path, f"{label} has non-string uses value")]
    if uses.startswith("./"):
        return []
    if uses.startswith("docker://"):
        image = uses.removeprefix("docker://")
        if "@sha256:" not in image:
            return [Finding(path, f"{label} Docker action must use an immutable sha256 digest")]
        return []
    if "@" not in uses:
        return [Finding(path, f"{label} action {uses!r} has no immutable revision")]
    action, revision = uses.rsplit("@", 1)
    if not _FULL_SHA.fullmatch(revision):
        return [Finding(path, f"{label} action {action!r} must use a full 40-character SHA")]
    return []


def _action_findings(path: Path, job_name: str, step_index: int, step: Any) -> list[Finding]:
    if not isinstance(step, dict) or "uses" not in step:
        return []

    uses = step["uses"]
    label = f"job {job_name!r} step {step_index}"
    findings = _external_action_finding(path, label, uses)
    if not isinstance(uses, str):
        return findings

    action = uses.rsplit("@", 1)[0]
    with_block = step.get("with")
    if action == "actions/checkout" and (
        not isinstance(with_block, dict)
        or not _is_false(with_block.get("persist-credentials"))
    ):
        findings.append(
            Finding(path, f"{label} actions/checkout must set persist-credentials: false")
        )

    if action == "actions/upload-artifact":
        if not isinstance(with_block, dict):
            findings.append(Finding(path, f"{label} upload-artifact requires a with mapping"))
        else:
            if not _positive_int(with_block.get("retention-days")):
                findings.append(
                    Finding(path, f"{label} upload-artifact needs positive retention-days")
                )
            if with_block.get("if-no-files-found") not in {"error", "warn", "ignore"}:
                findings.append(
                    Finding(path, f"{label} upload-artifact needs explicit if-no-files-found")
                )

    return findings


def audit_workflow(path: Path) -> list[Finding]:
    try:
        raw_text = path.read_text(encoding="utf-8")
        document = yaml.safe_load(raw_text)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return [Finding(path, f"cannot parse workflow: {exc}")]

    if not isinstance(document, dict):
        return [Finding(path, "workflow root must be a mapping")]

    findings: list[Finding] = []
    event_names, event_error = _event_names(_events(document))
    if event_error:
        findings.append(Finding(path, event_error))
    if "pull_request_target" in event_names:
        findings.append(Finding(path, "pull_request_target is forbidden for repository code"))

    findings.extend(_permission_findings(path, document.get("permissions"), scope="workflow"))

    concurrency = document.get("concurrency")
    if not isinstance(concurrency, dict) or not concurrency.get("group"):
        findings.append(Finding(path, "workflow must declare a concurrency group"))
    elif (
        not _is_false(concurrency.get("cancel-in-progress"))
        and concurrency.get("cancel-in-progress") is not True
    ):
        findings.append(Finding(path, "concurrency cancel-in-progress must be boolean"))

    jobs = document.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        return [*findings, Finding(path, "workflow must declare at least one job")]

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            findings.append(Finding(path, f"job {job_name!r} must be a mapping"))
            continue
        if "uses" in job:
            findings.append(
                Finding(path, f"job {job_name!r} reusable workflow calls are not supported")
            )
            findings.extend(_external_action_finding(path, f"job {job_name!r}", job.get("uses")))
            continue
        if not _positive_int(job.get("timeout-minutes")):
            findings.append(Finding(path, f"job {job_name!r} needs positive timeout-minutes"))
        runs_on = job.get("runs-on")
        if runs_on in _MUTABLE_RUNNERS:
            findings.append(
                Finding(path, f"job {job_name!r} must pin a concrete runner instead of {runs_on}")
            )
        if "permissions" in job:
            findings.extend(
                _permission_findings(
                    path,
                    job.get("permissions"),
                    scope=f"job {job_name!r}",
                )
            )

        steps = job.get("steps", [])
        if not isinstance(steps, list):
            findings.append(Finding(path, f"job {job_name!r} steps must be a list"))
            continue
        for index, step in enumerate(steps, start=1):
            findings.extend(_action_findings(path, str(job_name), index, step))

    if "pull_request" in event_names and _SECRET_REFERENCE.search(raw_text):
        findings.append(
            Finding(path, "pull-request workflows must not reference repository secrets")
        )

    return findings


def workflow_paths(repository_root: Path) -> list[Path]:
    workflow_dir = repository_root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return []
    return sorted(
        path
        for path in workflow_dir.iterdir()
        if path.is_file() and path.suffix in _WORKFLOW_SUFFIXES
    )


def audit_repository(repository_root: Path) -> list[Finding]:
    paths = workflow_paths(repository_root)
    if not paths:
        return [Finding(repository_root, "no GitHub Actions workflows found")]
    return [finding for path in paths for finding in audit_workflow(path)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "repository_root",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current directory)",
    )
    args = parser.parse_args()

    findings = audit_repository(args.repository_root.resolve())
    if findings:
        for finding in findings:
            print(f"ERROR: {finding.render()}")
        return 1

    print("GitHub Actions policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
