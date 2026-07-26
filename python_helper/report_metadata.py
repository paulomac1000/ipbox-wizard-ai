"""Completeness and reproducibility metadata for deterministic reports."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from .input_validation import strict_bool
from .tax_year_rules import get_tax_year_rules, strict_year

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_SOURCE_GLOBS = (
    "ipbox_algorytm.md",
    "python_helper/**/*.py",
    "tests/llm/oracle*.py",
    "tests/llm/allocation_guard*.py",
    "tests/llm/evaluator.py",
    "tests/llm/models.py",
    "tests/llm/output_schema*.py",
    "tests/llm/request_spec.py",
    "tests/llm/runner.py",
)


def _canonical_source_files(root: Path) -> tuple[tuple[str, Path], ...]:
    files: dict[str, Path] = {}
    for pattern in ENGINE_SOURCE_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                files[path.relative_to(root).as_posix()] = path
    if not files:
        raise RuntimeError(f"no canonical engine source files found under {root}")
    return tuple(sorted(files.items()))


@lru_cache(maxsize=8)
def _engine_source_hash(root_text: str) -> str:
    root = Path(root_text)
    digest = hashlib.sha256()
    for relative, path in _canonical_source_files(root):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def engine_source_hash(root: Path | None = None) -> str:
    """Hash the canonical deterministic engine and report-contract sources."""
    selected_root = (root or REPO_ROOT).resolve()
    return _engine_source_hash(str(selected_root))


def source_coverage_complete(input_data: Mapping[str, Any]) -> bool:
    """Return true only for an explicit, internally consistent closed-period declaration."""
    coverage = input_data.get("coverage")
    if coverage is None:
        return False
    if not isinstance(coverage, Mapping):
        raise ValueError("input.coverage must be a mapping")

    for field in ("expected_months", "imported_months"):
        value = coverage.get(field)
        if type(value) is not int:
            raise ValueError(f"input.coverage.{field} must be an integer")
        if value < 0:
            raise ValueError(f"input.coverage.{field} must be non-negative")
    expected = coverage["expected_months"]
    imported = coverage["imported_months"]
    if imported > expected:
        raise ValueError("input.coverage.imported_months cannot exceed expected_months")

    months = input_data.get("miesiace", [])
    if not isinstance(months, Sequence) or isinstance(months, str | bytes):
        raise ValueError("input.miesiace must be a list")
    if imported != len(months):
        raise ValueError("input.coverage.imported_months must equal the supplied month count")

    flags = (
        "invoices_complete",
        "kpir_complete",
        "work_records_complete",
        "period_closed",
    )
    complete_flags = [
        strict_bool(coverage.get(field), f"input.coverage.{field}") for field in flags
    ]
    confirmed_by = coverage.get("confirmed_by")
    if not isinstance(confirmed_by, str) or not confirmed_by.strip():
        raise ValueError("input.coverage.confirmed_by must be a non-empty string")
    return expected == imported and all(complete_flags)


def calculation_meta(input_data: Mapping[str, Any]) -> dict[str, Any]:
    """Build an auditable header with content-addressed engine identity."""
    year = strict_year(input_data.get("rok"), "input.rok")
    try:
        rules_source_ids = list(get_tax_year_rules(year).source_ids)
    except ValueError:
        rules_source_ids = ["UNVERIFIED_YEAR"]
    canonical = json.dumps(input_data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    source_hash = engine_source_hash()
    revision = os.getenv("IPBOX_CODE_REVISION") or f"engine:{source_hash}"
    calculated_at = os.getenv("IPBOX_CALCULATED_AT") or datetime.now(UTC).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    return {
        "engine_version": "ipbox-wizard-ai",
        "rule_pack": f"PL-PIT-IPBOX-{year}",
        "rules_source_ids": rules_source_ids,
        "input_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "engine_source_hash": source_hash,
        "calculated_at": calculated_at,
        "code_revision": revision,
    }
