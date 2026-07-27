#!/usr/bin/env python3
"""Allow either no committed cassettes or the exact complete benchmark matrix."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.vcr_precommit import validate_model  # noqa: E402
from tests.llm.models import BENCHMARK_MODELS, model_slug  # noqa: E402


def unexpected_model_directories(root: Path) -> set[str]:
    if not root.exists():
        return set()
    expected = {model_slug(model) for model in BENCHMARK_MODELS}
    discovered = {path.name for path in root.iterdir() if path.is_dir()}
    return discovered - expected


def unexpected_root_entries(root: Path) -> set[str]:
    """Return files or directories outside the canonical benchmark layout."""
    if not root.exists():
        return set()
    expected_directories = {model_slug(model) for model in BENCHMARK_MODELS}
    allowed_files = {".gitkeep"}
    unexpected: set[str] = set()
    for path in root.iterdir():
        if path.is_dir() and path.name in expected_directories:
            continue
        if path.is_file() and path.name in allowed_files:
            continue
        unexpected.add(path.name)
    return unexpected


def main(root: Path | None = None) -> int:
    root = root or ROOT / "tests/llm/vcr/cassettes"
    if not root.exists():
        print("Cassette policy: no cassette matrix committed yet — deterministic CI only")
        return 0
    cassette_files = [path for path in root.glob("*/*.yaml") if path.name != "_manifest.yaml"]
    manifests = list(root.glob("*/_manifest.yaml"))
    extras = unexpected_model_directories(root)
    root_extras = unexpected_root_entries(root)
    if not cassette_files and not manifests and not extras and not root_extras:
        print("Cassette policy: no cassette matrix committed yet — deterministic CI only")
        return 0

    errors = [f"unexpected model directory: {name}" for name in sorted(extras)]
    errors.extend(f"unexpected cassette root entry: {name}" for name in sorted(root_extras))
    errors.extend(error for model in BENCHMARK_MODELS for error in validate_model(model))
    if errors:
        print(
            "Cassette policy violation: partial, stale, extra or invalid matrix is committed.",
            file=sys.stderr,
        )
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    scenario_count = len(list((ROOT / "tests/llm/scenarios").glob("*.yaml")))
    print(
        f"Cassette policy: complete valid {len(BENCHMARK_MODELS)}-model matrix "
        f"({len(BENCHMARK_MODELS) * scenario_count} cassettes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
