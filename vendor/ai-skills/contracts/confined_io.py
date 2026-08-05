"""Shared bounded and repository-confined file I/O for security-sensitive tools."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

_ComponentSnapshot = tuple[tuple[Path, os.stat_result], ...]
_FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
_READ_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class ConfinedReadError(OSError):
    """Stable read failure with a machine-readable code and observed byte count."""

    code: str
    message: str
    byte_count: int = 0

    def __str__(self) -> str:
        return self.message


def supports_component_nofollow() -> bool:
    """Return whether directory-relative no-follow opens are available."""
    return bool(
        getattr(os, "O_NOFOLLOW", 0)
        and getattr(os, "O_DIRECTORY", 0)
        and os.open in getattr(os, "supports_dir_fd", set())
    )


def is_link_or_reparse(metadata: os.stat_result) -> bool:
    """Return whether metadata represents a symlink or Windows reparse point."""
    attributes = getattr(metadata, "st_file_attributes", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)


def component_snapshot(path: Path) -> _ComponentSnapshot:
    """Capture every existing path component without following link-like objects."""
    absolute = path.absolute()
    parts = absolute.parts
    if not parts:
        raise OSError("input path has no components")

    current = Path(parts[0])
    snapshot: list[tuple[Path, os.stat_result]] = []
    for component in parts[1:]:
        current /= component
        metadata = os.lstat(current)
        if is_link_or_reparse(metadata):
            raise OSError(f"refusing reparse or symlink component: {current}")
        snapshot.append((current, metadata))
    if not snapshot:
        raise OSError("input path has no final component")
    return tuple(snapshot)


def snapshot_is_current(snapshot: _ComponentSnapshot) -> bool:
    """Return whether every captured component still has the same identity."""
    try:
        return all(os.path.samestat(expected, os.lstat(path)) for path, expected in snapshot)
    except OSError:
        return False


def open_component_safe(path: Path, flags: int) -> int:
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


def open_stable(
    path: Path,
    flags: int,
    *,
    component_nofollow: bool | None = None,
) -> tuple[int, _ComponentSnapshot | None]:
    """Open with component no-follow, or bind every component on fallback platforms."""
    use_component_nofollow = supports_component_nofollow() if component_nofollow is None else component_nofollow
    if use_component_nofollow:
        return open_component_safe(path, flags), None

    snapshot = component_snapshot(path)
    expected = snapshot[-1][1]
    descriptor = os.open(path, flags)
    metadata = os.fstat(descriptor)
    if not os.path.samestat(expected, metadata) or not snapshot_is_current(snapshot):
        os.close(descriptor)
        raise OSError("path identity changed while opening")
    return descriptor, snapshot


def confined_candidate(path: Path, repository_root: Path) -> tuple[Path, Path]:
    """Normalize one candidate and prove lexical containment in a trusted root."""
    root = repository_root.resolve(strict=True)
    candidate = Path(os.path.normpath(path.absolute()))
    candidate.relative_to(root)
    return candidate, root


def read_utf8_bounded(path: Path, repository_root: Path, max_bytes: int) -> tuple[str, int]:
    """Read one stable regular UTF-8 file using a strict maximum allocation."""
    try:
        candidate, _root = confined_candidate(path, repository_root)
        descriptor, snapshot = open_stable(
            candidate,
            os.O_RDONLY | getattr(os, "O_BINARY", 0),
        )
    except (OSError, ValueError) as error:
        raise ConfinedReadError("input.read-error", f"Could not open input file safely: {error}") from error

    payload = b""
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ConfinedReadError("input.read-error", "Input is not a regular file.")
        if metadata.st_size > max_bytes:
            raise ConfinedReadError(
                "input.too-large",
                f"Input file is {metadata.st_size} bytes; maximum supported size is {max_bytes} bytes.",
                metadata.st_size,
            )

        remaining = max_bytes + 1
        chunks: list[bytes] = []
        while remaining > 0:
            chunk = os.read(descriptor, min(_READ_CHUNK_BYTES, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if snapshot is not None and not snapshot_is_current(snapshot):
            raise ConfinedReadError(
                "input.read-error",
                "Input path identity changed while reading; refusing the result.",
            )
    except ConfinedReadError:
        raise
    except OSError as error:
        raise ConfinedReadError("input.read-error", f"Could not read input file safely: {error}") from error
    finally:
        os.close(descriptor)

    if len(payload) > max_bytes:
        raise ConfinedReadError(
            "input.too-large",
            f"Input file exceeds the maximum supported size of {max_bytes} bytes.",
            len(payload),
        )
    try:
        return payload.decode("utf-8"), len(payload)
    except UnicodeDecodeError as error:
        raise ConfinedReadError(
            "input.invalid-utf8",
            f"Input file is not valid UTF-8 at byte {error.start}.",
            len(payload),
        ) from error
