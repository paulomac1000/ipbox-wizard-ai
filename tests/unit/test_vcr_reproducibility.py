"""Regression tests for content-addressed VCR reproducibility."""

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
