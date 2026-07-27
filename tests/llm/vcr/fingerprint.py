"""Content-addressed identity of the engine, VCR harness, scenario and request."""

from __future__ import annotations

import hashlib
from pathlib import Path

from python_helper.report_metadata import engine_source_hash

FINGERPRINT_NAMESPACE = "canonical-source"
ROOT = Path(__file__).resolve().parents[3]
VCR_SOURCE_GLOBS = (
    "tests/llm/vcr/**/*.py",
    "scripts/benchmark_report.py",
    "scripts/check_cassette_policy.py",
    "scripts/refresh_vcr_metadata.py",
    "scripts/vcr_precommit.py",
)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _tree_hash(root: Path, patterns: tuple[str, ...]) -> str:
    files: dict[str, Path] = {}
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file():
                files[path.relative_to(root).as_posix()] = path
    if not files:
        raise RuntimeError("no VCR source files found for fingerprinting")
    digest = hashlib.sha256()
    for relative, path in sorted(files.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def vcr_source_hash(root: Path | None = None) -> str:
    return _tree_hash((root or ROOT).resolve(), VCR_SOURCE_GLOBS)


def compute_fingerprint(scenario_path: Path, request_hash: str) -> str:
    material = "\0".join(
        (
            FINGERPRINT_NAMESPACE,
            engine_source_hash(ROOT),
            vcr_source_hash(ROOT),
            file_hash(scenario_path),
            request_hash,
        )
    )
    return f"{FINGERPRINT_NAMESPACE}_{content_hash(material)}"
