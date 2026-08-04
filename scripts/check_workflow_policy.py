#!/usr/bin/env python3
"""Hardened entrypoint for the trusted GitHub Actions policy auditor."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from pathlib import Path

import check_github_actions_policy_impl as _impl

MAX_DISCOVERY_ENTRIES = 4096
MAX_WORKFLOW_FILES = _impl.MAX_WORKFLOW_FILES
MAX_WORKFLOW_BYTES = _impl.MAX_WORKFLOW_BYTES
MAX_TOTAL_BYTES = _impl.MAX_TOTAL_BYTES
Finding = _impl.Finding

_ComponentSnapshot = tuple[tuple[Path, os.stat_result], ...]
_FILE_ATTRIBUTE_REPARSE_POINT = 0x0400


def _supports_component_nofollow() -> bool:
    return bool(
        getattr(os, "O_NOFOLLOW", 0)
        and getattr(os, "O_DIRECTORY", 0)
        and os.open in getattr(os, "supports_dir_fd", set())
    )


def _is_link_or_reparse(metadata: os.stat_result) -> bool:
    attributes = getattr(metadata, "st_file_attributes", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)


def _component_snapshot(path: Path) -> _ComponentSnapshot:
    """Capture every existing component without following links or reparse points."""
    absolute = path.absolute()
    parts = absolute.parts
    if not parts:
        raise OSError("input path has no components")

    current = Path(parts[0])
    snapshot: list[tuple[Path, os.stat_result]] = []
    for component in parts[1:]:
        current /= component
        metadata = os.lstat(current)
        if _is_link_or_reparse(metadata):
            raise OSError(f"refusing reparse or symlink component: {current}")
        snapshot.append((current, metadata))
    return tuple(snapshot)


def _snapshot_is_current(snapshot: _ComponentSnapshot) -> bool:
    try:
        return all(os.path.samestat(expected, os.lstat(path)) for path, expected in snapshot)
    except OSError:
        return False


def _open_component_safe(path: Path, flags: int) -> int:
    """Open an absolute path without following intermediate or final symlinks."""
    absolute = path.absolute()
    parts = absolute.parts
    if len(parts) < 2:
        raise OSError("input path has no final component")
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory = os.open(parts[0], directory_flags)
    try:
        for component in parts[1:-1]:
            child = os.open(component, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = child
        return os.open(parts[-1], flags | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory)
    finally:
        os.close(directory)


def _open_stable(path: Path, flags: int) -> tuple[int, _ComponentSnapshot | None]:
    """Open with component no-follow where available, otherwise bind every component."""
    if _supports_component_nofollow():
        return _open_component_safe(path, flags), None

    snapshot = _component_snapshot(path)
    expected = snapshot[-1][1]
    descriptor = os.open(path, flags)
    metadata = os.fstat(descriptor)
    if not os.path.samestat(expected, metadata) or not _snapshot_is_current(snapshot):
        os.close(descriptor)
        raise OSError("path identity changed while opening")
    return descriptor, snapshot


def _read_workflow(path: Path, repository_root: Path) -> tuple[str | None, str | None]:
    """Read a bounded, stable workflow without following replaced path components."""
    try:
        root = repository_root.resolve(strict=True)
        candidate = path.absolute()
        candidate.relative_to(root)
        descriptor, snapshot = _open_stable(
            candidate,
            os.O_RDONLY | getattr(os, "O_BINARY", 0),
        )
    except (OSError, ValueError) as exc:
        return None, f"cannot read workflow safely: {exc}"

    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            return None, "workflow path must be a regular file"
        if metadata.st_size > MAX_WORKFLOW_BYTES:
            return None, f"workflow exceeds {MAX_WORKFLOW_BYTES} byte limit"
        remaining = MAX_WORKFLOW_BYTES + 1
        chunks: list[bytes] = []
        while remaining > 0:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if snapshot is not None and not _snapshot_is_current(snapshot):
            return None, "workflow identity changed while reading"
    except OSError as exc:
        return None, f"cannot read workflow safely: {exc}"
    finally:
        os.close(descriptor)

    if len(payload) > MAX_WORKFLOW_BYTES:
        return None, f"workflow exceeds {MAX_WORKFLOW_BYTES} byte limit"
    try:
        return payload.decode("utf-8"), None
    except UnicodeError as exc:
        return None, f"cannot read workflow safely: {exc}"


def _collect_workflow_entries(
    entries: Iterator[os.DirEntry[str]],
    workflow_dir: Path,
) -> tuple[list[Path], list[Finding]]:
    paths: list[Path] = []
    findings: list[Finding] = []
    total_bytes = 0

    for entries_seen, entry in enumerate(entries, start=1):
        if entries_seen > MAX_DISCOVERY_ENTRIES:
            findings.append(
                Finding(
                    workflow_dir,
                    f"workflow directory entry count exceeds {MAX_DISCOVERY_ENTRIES}",
                )
            )
            break
        if Path(entry.name).suffix.casefold() not in _impl._WORKFLOW_SUFFIXES:
            continue
        if len(paths) >= MAX_WORKFLOW_FILES:
            findings.append(Finding(workflow_dir, f"workflow count exceeds {MAX_WORKFLOW_FILES}"))
            break
        entry_path = workflow_dir / entry.name
        try:
            metadata = entry.stat(follow_symlinks=False)
        except OSError as exc:
            findings.append(Finding(entry_path, f"cannot inspect workflow: {exc}"))
            continue
        if _is_link_or_reparse(metadata) or not stat.S_ISREG(metadata.st_mode):
            findings.append(Finding(entry_path, "workflow path must be a regular non-symlink file"))
            continue
        total_bytes += metadata.st_size
        if total_bytes > MAX_TOTAL_BYTES:
            findings.append(Finding(workflow_dir, f"workflow bytes exceed {MAX_TOTAL_BYTES} total limit"))
            break
        paths.append(entry_path)

    paths.sort(key=lambda item: item.name)
    return paths, findings


def workflow_paths(repository_root: Path) -> tuple[list[Path], list[Finding]]:
    """Enumerate workflow candidates incrementally under a global entry budget."""
    workflow_dir = repository_root / ".github" / "workflows"

    if _supports_component_nofollow() and os.scandir in getattr(os, "supports_fd", set()):
        try:
            directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            descriptor, _ = _open_stable(workflow_dir, directory_flags)
        except FileNotFoundError:
            return [], [Finding(repository_root, "no GitHub Actions workflows found")]
        except OSError as exc:
            return [], [Finding(workflow_dir, f"cannot enumerate workflows: {exc}")]
        try:
            if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
                return [], [Finding(workflow_dir, "workflow directory must be a regular directory")]
            with os.scandir(descriptor) as entries:
                return _collect_workflow_entries(entries, workflow_dir)
        except OSError as exc:
            return [], [Finding(workflow_dir, f"cannot enumerate workflows: {exc}")]
        finally:
            os.close(descriptor)

    try:
        snapshot = _component_snapshot(workflow_dir)
        if not stat.S_ISDIR(snapshot[-1][1].st_mode):
            return [], [Finding(workflow_dir, "workflow directory must be a regular directory")]
        with os.scandir(workflow_dir) as entries:
            paths, findings = _collect_workflow_entries(entries, workflow_dir)
        if not _snapshot_is_current(snapshot):
            return [], [Finding(workflow_dir, "workflow directory identity changed while enumerating")]
        return paths, findings
    except FileNotFoundError:
        return [], [Finding(repository_root, "no GitHub Actions workflows found")]
    except OSError as exc:
        return [], [Finding(workflow_dir, f"cannot enumerate workflows: {exc}")]


_impl._read_workflow = _read_workflow
_impl.workflow_paths = workflow_paths

audit_workflow = _impl.audit_workflow
audit_repository = _impl.audit_repository
_event_names = _impl._event_names
main = _impl.main


if __name__ == "__main__":
    raise SystemExit(main())
