#!/usr/bin/env python3
"""Allow either no committed cassettes or a complete valid benchmark matrix."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.vcr_precommit import validate_model  # noqa: E402
from tests.llm.models import BENCHMARK_MODELS  # noqa: E402


def main() -> int:
    root = ROOT / "tests/llm/vcr/cassettes"
    cassette_files = [path for path in root.glob("*/*.yaml") if path.name != "_manifest.yaml"]
    manifests = list(root.glob("*/_manifest.yaml"))
    if not cassette_files and not manifests:
        print("Cassette policy: no cassette matrix committed yet — deterministic CI only")
        return 0

    errors = [error for model in BENCHMARK_MODELS for error in validate_model(model)]
    if errors:
        print(
            "Cassette policy violation: partial, stale or invalid cassette matrix is committed.",
            file=sys.stderr,
        )
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Cassette policy: complete valid 3-model matrix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
