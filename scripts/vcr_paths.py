"""Shared fail-closed path resolution for VCR storage."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from scripts.local_env import load_local_env

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASSETTE_ROOT = ROOT / "tests/llm/vcr/cassettes"


def _user_scope() -> str:
    """Return a stable, filesystem-safe scope for the current OS user."""
    getuid = getattr(os, "getuid", None)
    if callable(getuid):
        return str(getuid())
    identity = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown-user"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]


DEFAULT_REJECTED_ROOT = Path(tempfile.gettempdir()) / f"ipbox_llm_rejected_{_user_scope()}"


def resolve_storage_path(value: str | Path, *, name: str) -> Path:
    """Return one absolute, non-empty path for parent and child processes."""
    if isinstance(value, Path) and not value.parts:
        raise ValueError(f"{name} must not be empty")
    raw = str(value)
    if not raw.strip():
        raise ValueError(f"{name} must not be empty")
    return Path(raw).expanduser().resolve(strict=False)


def _effective_environ(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    if environ is not None:
        return environ
    load_local_env()
    return os.environ


def resolve_cassette_root(
    value: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve an explicit root or the process/.env VCR cassette root."""
    selected = value
    if selected is None:
        current = _effective_environ(environ)
        selected = current.get("VCR_CASSETTES_ROOT", str(DEFAULT_CASSETTE_ROOT))
    return resolve_storage_path(selected, name="VCR_CASSETTES_ROOT")


def resolve_cassette_root_or_error(
    parser: argparse.ArgumentParser,
    value: str | Path | None = None,
) -> Path:
    """Resolve a cassette root or terminate an argparse CLI with a clear error."""
    try:
        return resolve_cassette_root(value)
    except ValueError as exc:
        parser.error(str(exc))


def resolve_rejected_root(
    value: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve an explicit root or the process/.env rejected-attempt root."""
    selected = value
    if selected is None:
        current = _effective_environ(environ)
        selected = current.get("VCR_REJECTED_ROOT", str(DEFAULT_REJECTED_ROOT))
    return resolve_storage_path(selected, name="VCR_REJECTED_ROOT")
