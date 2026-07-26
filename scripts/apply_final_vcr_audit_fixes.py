#!/usr/bin/env python3
"""One-time source patch for the final VCR reproducibility audit."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(relative: str, content: str) -> None:
    (ROOT / relative).write_text(content, encoding="utf-8")


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected block not found in {relative}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


write(
    "python_helper/report_metadata.py",
    '''"""Completeness and reproducibility metadata for deterministic reports."""

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
        digest.update(b"\\0")
        digest.update(path.read_bytes())
        digest.update(b"\\0")
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
''',
)

write(
    "tests/llm/vcr/fingerprint.py",
    '''"""Content-addressed identity of the engine, VCR harness, scenario and request."""

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
        digest.update(b"\\0")
        digest.update(path.read_bytes())
        digest.update(b"\\0")
    return digest.hexdigest()


def vcr_source_hash(root: Path | None = None) -> str:
    return _tree_hash((root or ROOT).resolve(), VCR_SOURCE_GLOBS)


def compute_fingerprint(scenario_path: Path, request_hash: str) -> str:
    material = "\\0".join(
        (
            FINGERPRINT_NAMESPACE,
            engine_source_hash(ROOT),
            vcr_source_hash(ROOT),
            file_hash(scenario_path),
            request_hash,
        )
    )
    return f"{FINGERPRINT_NAMESPACE}_{content_hash(material)}"
''',
)

write(
    "tests/llm/vcr/cassette.py",
    '''"""Versioned cassette and per-model manifest formats."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

CASSETTE_FORMAT_VERSION = 4
MANIFEST_FORMAT_VERSION = 3


def _meta_equal_without_calculated_at(ma: dict | None, mb: dict | None) -> bool:
    ma = ma or {}
    mb = mb or {}
    return all(
        ma.get(key) == mb.get(key)
        for key in set(ma) | set(mb)
        if key != "calculated_at"
    )


def parsed_response_equal_ignoring_meta_timestamp(a: dict, b: dict) -> bool:
    if type(a) is not type(b):
        return False
    if a.keys() != b.keys():
        return False
    for key in a:
        if isinstance(a[key], dict):
            if key == "calculation_meta":
                if not _meta_equal_without_calculated_at(a[key], b[key]):
                    return False
                continue
            if not parsed_response_equal_ignoring_meta_timestamp(a[key], b[key]):
                return False
        elif isinstance(a[key], list):
            if len(a[key]) != len(b[key]):
                return False
            for value_a, value_b in zip(a[key], b[key]):
                if isinstance(value_a, (dict, list)):
                    if not parsed_response_equal_ignoring_meta_timestamp(value_a, value_b):
                        return False
                elif value_a != value_b:
                    return False
        elif a[key] != b[key]:
            return False
    return True


def _require_nonempty_text(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"cassette meta {name} must be a non-empty string")


def _require_optional_nonnegative_int(name: str, value: Any) -> None:
    if value is not None and (type(value) is not int or value < 0):
        raise ValueError(f"cassette meta {name} must be a non-negative integer or null")


def _require_nonnegative_finite_number(name: str, value: Any, *, optional: bool) -> None:
    if optional and value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"cassette meta {name} must be a finite non-negative number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"cassette meta {name} must be a finite non-negative number")


@dataclass(frozen=True, slots=True)
class CassetteMeta:
    scenario_id: str
    scenario_name: str
    provider: str
    requested_model: str
    returned_model: str | None
    fingerprint: str
    request_hash: str
    recorded_at: str
    request_id: str | None
    finish_reason: str | None
    native_finish_reason: str | None
    system_fingerprint: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost: float | None
    recording_duration_seconds: float
    cassette_format_version: int = CASSETTE_FORMAT_VERSION

    def __post_init__(self) -> None:
        if type(self.cassette_format_version) is not int or (
            self.cassette_format_version != CASSETTE_FORMAT_VERSION
        ):
            raise ValueError(
                f"cassette_format_version must equal {CASSETTE_FORMAT_VERSION}"
            )
        for name in (
            "scenario_id",
            "scenario_name",
            "provider",
            "requested_model",
            "returned_model",
            "fingerprint",
            "request_hash",
            "recorded_at",
            "finish_reason",
        ):
            _require_nonempty_text(name, getattr(self, name))
        if len(self.request_hash) != 64 or any(
            character not in "0123456789abcdef" for character in self.request_hash
        ):
            raise ValueError("cassette meta request_hash must be 64 lowercase hex characters")
        try:
            recorded = datetime.fromisoformat(self.recorded_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("cassette meta recorded_at must be ISO-8601") from exc
        if recorded.tzinfo is None:
            raise ValueError("cassette meta recorded_at must include a timezone")
        for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
            _require_optional_nonnegative_int(name, getattr(self, name))
        _require_nonnegative_finite_number("cost", self.cost, optional=True)
        _require_nonnegative_finite_number(
            "recording_duration_seconds",
            self.recording_duration_seconds,
            optional=False,
        )


@dataclass(frozen=True, slots=True)
class Cassette:
    meta: CassetteMeta
    response: str
    parsed_response: dict[str, Any]

    def to_yaml(self) -> str:
        return yaml.safe_dump(
            {
                "meta": asdict(self.meta),
                "response": self.response,
                "parsed_response": self.parsed_response,
            },
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(self.to_yaml(), encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def load(cls, path: Path) -> Cassette:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Cassette {path} must be a mapping")
        meta_data = data.get("meta")
        if not isinstance(meta_data, dict):
            raise ValueError(f"Cassette {path} has no meta mapping")
        if meta_data.get("cassette_format_version") != CASSETTE_FORMAT_VERSION:
            raise ValueError(
                f"Unsupported cassette version {meta_data.get('cassette_format_version')!r}; "
                f"expected {CASSETTE_FORMAT_VERSION}"
            )
        meta = CassetteMeta(**meta_data)
        response = data.get("response")
        parsed = data.get("parsed_response")
        if not isinstance(response, str) or not response.strip():
            raise ValueError(f"Cassette {path} has an empty response")
        if not isinstance(parsed, dict):
            raise ValueError(f"Cassette {path} has no parsed response")
        return cls(meta=meta, response=response, parsed_response=parsed)


@dataclass(slots=True)
class CassetteManifest:
    model: str
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path, model: str) -> CassetteManifest:
        if not path.exists():
            return cls(model=model)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("manifest_format_version") != MANIFEST_FORMAT_VERSION:
            raise ValueError(f"Unsupported manifest version in {path}")
        if data.get("model") != model:
            raise ValueError(f"Manifest model mismatch in {path}")
        entries = data.get("entries")
        if not isinstance(entries, dict):
            raise ValueError(f"Manifest entries must be a mapping in {path}")
        return cls(model=model, entries=entries)

    def update(self, cassette: Cassette, filename: str) -> None:
        calculation_meta = cassette.parsed_response.get("calculation_meta")
        if not isinstance(calculation_meta, dict):
            raise ValueError("cassette parsed_response has no calculation_meta")
        engine_hash = calculation_meta.get("engine_source_hash")
        if not isinstance(engine_hash, str) or len(engine_hash) != 64:
            raise ValueError("cassette calculation_meta has no valid engine_source_hash")
        self.entries[cassette.meta.scenario_id] = {
            "file": filename,
            "fingerprint": cassette.meta.fingerprint,
            "request_hash": cassette.meta.request_hash,
            "engine_source_hash": engine_hash,
            "recorded_at": cassette.meta.recorded_at,
            "returned_model": cassette.meta.returned_model,
            "cost": cassette.meta.cost,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "manifest_format_version": MANIFEST_FORMAT_VERSION,
            "model": self.model,
            "generated_at": datetime.now(UTC).isoformat(),
            "entries": dict(sorted(self.entries.items())),
        }
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        temporary.replace(path)
''',
)

write(
    "scripts/refresh_vcr_metadata.py",
    '''#!/usr/bin/env python3
"""Refresh cassette-derived metadata from existing raw responses without API calls."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_helper.report_metadata import engine_source_hash  # noqa: E402
from tests.llm.models import BENCHMARK_MODELS  # noqa: E402
from tests.llm.oracle import validate_scenario  # noqa: E402
from tests.llm.runner import LLMTestRunner  # noqa: E402
from tests.llm.vcr.cassette import (  # noqa: E402
    CASSETTE_FORMAT_VERSION,
    Cassette,
    CassetteManifest,
)
from tests.llm.vcr.config import VCRConfig  # noqa: E402
from tests.llm.vcr.fingerprint import compute_fingerprint  # noqa: E402

CASSETTE_ROOT = ROOT / "tests/llm/vcr/cassettes"
SCENARIO_ROOT = ROOT / "tests/llm/scenarios"


def refresh_model(model: str, *, write: bool) -> int:
    os.environ.update(
        {
            "LLM_PROVIDER": "openrouter",
            "LLM_MODEL": model,
            "VCR_MODE": "playback",
            "VCR_CASSETTES_ROOT": str(CASSETTE_ROOT),
            "IPBOX_CODE_REVISION": f"engine:{engine_source_hash(ROOT)}",
        }
    )
    config = VCRConfig()
    runner = LLMTestRunner(None)
    manifest = CassetteManifest(model=model)
    algorithm = (ROOT / "ipbox_algorytm.md").read_text(encoding="utf-8")
    expected_ids: set[str] = set()
    changed = 0

    for scenario_path in sorted(SCENARIO_ROOT.glob("*.yaml")):
        scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
        validate_scenario(scenario)
        scenario_id = str(scenario["meta"]["id"])
        expected_ids.add(scenario_id)
        cassette_path = config.cassette_path(scenario_id)
        if not cassette_path.exists():
            raise FileNotFoundError(f"{model}: missing cassette {scenario_id}")
        cassette = Cassette.load(cassette_path)
        if cassette.meta.requested_model != model or cassette.meta.returned_model != model:
            raise ValueError(f"{model}/{scenario_id}: model identity mismatch")

        previous_meta = cassette.parsed_response.get("calculation_meta") or {}
        calculated_at = previous_meta.get("calculated_at") or cassette.meta.recorded_at
        os.environ["IPBOX_CALCULATED_AT"] = str(calculated_at)
        prompt = runner.build_prompt(algorithm, scenario)
        request = runner.request_spec(prompt, config)
        request_hash = request.request_hash()
        parsed = runner.validate_semantics(cassette.response, scenario)
        refreshed = Cassette(
            meta=replace(
                cassette.meta,
                request_hash=request_hash,
                fingerprint=compute_fingerprint(scenario_path, request_hash),
                cassette_format_version=CASSETTE_FORMAT_VERSION,
            ),
            response=cassette.response,
            parsed_response=parsed,
        )
        manifest.update(refreshed, cassette_path.name)
        if refreshed.to_yaml() != cassette.to_yaml():
            changed += 1
        if write:
            refreshed.save(cassette_path)

    actual_ids = {
        path.stem for path in config.model_directory.glob("*.yaml") if path.name != "_manifest.yaml"
    }
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        raise ValueError(f"{model}: cassette set mismatch; missing={missing}, extra={extra}")
    if write:
        manifest.save(config.manifest_path)
    print(f"{model}: validated={len(expected_ids)}, refreshed={changed}, write={write}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--model")
    group.add_argument("--all-models", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    models = BENCHMARK_MODELS if args.all_models else (args.model,)
    total = sum(refresh_model(model, write=args.write) for model in models)
    print(f"Total cassette payloads requiring refresh: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
)

write(
    "tests/unit/test_vcr_reproducibility.py",
    '''"""Regression tests for content-addressed VCR reproducibility."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from python_helper.report_metadata import calculation_meta, engine_source_hash
from tests.llm.models import BENCHMARK_MODELS
from tests.llm.vcr.cassette import (
    CassetteMeta,
    parsed_response_equal_ignoring_meta_timestamp,
)

ROOT = Path(__file__).resolve().parents[2]


def valid_meta() -> CassetteMeta:
    return CassetteMeta(
        scenario_id="scenario",
        scenario_name="Scenario",
        provider="openrouter",
        requested_model="model/name",
        returned_model="model/name",
        fingerprint="canonical-source_" + "a" * 64,
        request_hash="b" * 64,
        recorded_at="2026-07-25T23:20:56+00:00",
        request_id="request",
        finish_reason="stop",
        native_finish_reason="STOP",
        system_fingerprint=None,
        prompt_tokens=1,
        completion_tokens=2,
        total_tokens=3,
        cost=0.01,
        recording_duration_seconds=0.5,
    )


def test_engine_source_hash_is_stable_and_content_sensitive(tmp_path: Path) -> None:
    (tmp_path / "python_helper").mkdir()
    source = tmp_path / "python_helper" / "engine.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    first = engine_source_hash(tmp_path)
    assert first == engine_source_hash(tmp_path)
    source.write_text("VALUE = 2\n", encoding="utf-8")
    from python_helper import report_metadata

    report_metadata._engine_source_hash.cache_clear()
    assert engine_source_hash(tmp_path) != first


def test_calculation_meta_does_not_depend_on_github_sha(monkeypatch) -> None:
    monkeypatch.delenv("IPBOX_CODE_REVISION", raising=False)
    monkeypatch.setenv("IPBOX_CALCULATED_AT", "2026-07-25T00:00:00Z")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    first = calculation_meta({"rok": 2025})
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    second = calculation_meta({"rok": 2025})
    assert first == second
    assert first["code_revision"] == f"engine:{first['engine_source_hash']}"
    assert len(first["engine_source_hash"]) == 64


def test_parsed_response_ignores_only_calculated_at() -> None:
    source_hash = "a" * 64
    first = {
        "calculation_meta": {
            "calculated_at": "2026-01-01T00:00:00Z",
            "code_revision": f"engine:{source_hash}",
            "engine_source_hash": source_hash,
        },
        "result": {"tax": 1},
    }
    timestamp_changed = {
        **first,
        "calculation_meta": {
            **first["calculation_meta"],
            "calculated_at": "2026-01-02T00:00:00Z",
        },
    }
    assert parsed_response_equal_ignoring_meta_timestamp(first, timestamp_changed)
    assert not parsed_response_equal_ignoring_meta_timestamp(
        first,
        {
            **first,
            "calculation_meta": {
                **first["calculation_meta"],
                "engine_source_hash": "b" * 64,
            },
        },
    )
    assert not parsed_response_equal_ignoring_meta_timestamp(
        first,
        {
            **first,
            "calculation_meta": {
                **first["calculation_meta"],
                "code_revision": "engine:" + "b" * 64,
            },
        },
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("provider", ""),
        ("recorded_at", "not-a-date"),
        ("prompt_tokens", -1),
        ("prompt_tokens", "1"),
        ("cost", float("nan")),
        ("cost", -0.01),
        ("recording_duration_seconds", float("inf")),
        ("recording_duration_seconds", -1),
    ),
)
def test_cassette_meta_rejects_invalid_runtime_boundaries(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        replace(valid_meta(), **{field: value})


def test_manual_workflow_models_match_registry_exactly() -> None:
    workflow = yaml.load(
        (ROOT / ".github/workflows/llm-benchmark.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    options = workflow["on"]["workflow_dispatch"]["inputs"]["model"]["options"]
    assert tuple(options) == ("all", *BENCHMARK_MODELS)
''',
)

replace_once(
    "tests/llm/output_schema.py",
    '''        "input_hash",
        "calculated_at",
        "code_revision",
''',
    '''        "input_hash",
        "engine_source_hash",
        "calculated_at",
        "code_revision",
''',
)
replace_once(
    "tests/llm/output_schema.py",
    '''        "input_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "calculated_at": {"type": "string", "format": "date-time"},
        "code_revision": {"type": "string", "minLength": 1},
''',
    '''        "input_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "engine_source_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "calculated_at": {"type": "string", "format": "date-time"},
        "code_revision": {
            "type": "string",
            "minLength": 1,
            "not": {"const": "unavailable"},
        },
''',
)

replace_once(
    "scripts/vcr_precommit.py",
    '''from tests.llm.models import BENCHMARK_MODELS  # noqa: E402
''',
    '''from python_helper.report_metadata import engine_source_hash  # noqa: E402
from tests.llm.models import BENCHMARK_MODELS  # noqa: E402
''',
)
replace_once(
    "scripts/vcr_precommit.py",
    '''    expected_ids: set[str] = set()
    algorithm = (ROOT / "ipbox_algorytm.md").read_text(encoding="utf-8")
''',
    '''    expected_ids: set[str] = set()
    expected_engine_hash = engine_source_hash(ROOT)
    algorithm = (ROOT / "ipbox_algorytm.md").read_text(encoding="utf-8")
''',
)
replace_once(
    "scripts/vcr_precommit.py",
    '''            if cassette.meta.fingerprint != fingerprint:
                errors.append(f"{model}/{scenario_id}: fingerprint mismatch")
            reparsed = runner.validate_semantics(cassette.response, scenario)
''',
    '''            if cassette.meta.fingerprint != fingerprint:
                errors.append(f"{model}/{scenario_id}: fingerprint mismatch")
            stored_calculation_meta = cassette.parsed_response.get("calculation_meta")
            stored_engine_hash = (
                stored_calculation_meta.get("engine_source_hash")
                if isinstance(stored_calculation_meta, dict)
                else None
            )
            if stored_engine_hash != expected_engine_hash:
                errors.append(f"{model}/{scenario_id}: engine_source_hash mismatch")
            reparsed = runner.validate_semantics(cassette.response, scenario)
''',
)
replace_once(
    "scripts/vcr_precommit.py",
    '''                if entry.get("fingerprint") != fingerprint:
                    errors.append(f"{model}/{scenario_id}: manifest fingerprint mismatch")
                if entry.get("returned_model") != cassette.meta.returned_model:
''',
    '''                if entry.get("fingerprint") != fingerprint:
                    errors.append(f"{model}/{scenario_id}: manifest fingerprint mismatch")
                if entry.get("engine_source_hash") != expected_engine_hash:
                    errors.append(f"{model}/{scenario_id}: manifest engine_source_hash mismatch")
                if entry.get("returned_model") != cassette.meta.returned_model:
''',
)

replace_once(
    "tests/llm/vcr/recorder.py",
    '''        parsed = validate_response(cassette.response)
        if not parsed_response_equal_ignoring_meta_timestamp(parsed, cassette.parsed_response):
''',
    '''        parsed = validate_response(cassette.response)
        calculation_meta = parsed.get("calculation_meta")
        engine_hash = (
            calculation_meta.get("engine_source_hash")
            if isinstance(calculation_meta, dict)
            else None
        )
        if entry.get("engine_source_hash") != engine_hash:
            raise CassetteStaleError("Manifest engine_source_hash mismatch")
        if not parsed_response_equal_ignoring_meta_timestamp(parsed, cassette.parsed_response):
''',
)

for relative in (
    ".github/workflows/llm-benchmark.yml",
    "README.md",
    "docs/testing.md",
    "docs/model-diversity-benchmark.md",
):
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "mistralai/ministral-3b-2512",
        "mistralai/mistral-small-24b-instruct-2501",
    )
    path.write_text(text, encoding="utf-8")

readme = ROOT / "README.md"
readme_text = readme.read_text(encoding="utf-8")
anchor = "Każdy raport zawiera `calculation_meta`: identyfikator silnika, rule pack roku, źródła reguł, SHA-256 wejścia, czas obliczenia i rewizję kodu."
replacement = (
    anchor
    + "\n\n`calculation_meta.engine_source_hash` jest autorytatywną, stabilną tożsamością treści "
    "silnika i kontraktu raportu. `code_revision` domyślnie używa tej tożsamości w formie "
    "`engine:<hash>`; chwilowy `GITHUB_SHA` nie wpływa na semantyczny playback kaset."
)
if anchor not in readme_text:
    raise RuntimeError("README calculation_meta anchor not found")
readme.write_text(readme_text.replace(anchor, replacement, 1), encoding="utf-8")

agents = ROOT / "AGENTS.md"
ag_text = agents.read_text(encoding="utf-8")
ag_anchor = "- Finalny raport musi zawierać `calculation_meta` z hashem wejścia, źródłami reguł i rewizją kodu."
ag_replacement = (
    ag_anchor
    + "\n- Semantyczną tożsamością wersji jest `engine_source_hash`; nie używaj chwilowego "
    "`GITHUB_SHA` jako fingerprintu wyniku ani kasety."
)
if ag_anchor not in ag_text:
    raise RuntimeError("AGENTS calculation_meta anchor not found")
agents.write_text(ag_text.replace(ag_anchor, ag_replacement, 1), encoding="utf-8")

print("Applied final VCR audit source fixes")
