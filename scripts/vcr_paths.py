"""Shared fail-closed path resolution for VCR storage."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from scripts.local_env import load_local_env

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASSETTE_ROOT = ROOT / "tests/llm/vcr/cassettes"
DEFAULT_REJECTED_ROOT = Path("/tmp/ipbox_llm_rejected")


def resolve_storage_path(value: str | Path, *, name: str) -> Path:
    """Return one absolute, non-empty path for parent and child processes."""
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
