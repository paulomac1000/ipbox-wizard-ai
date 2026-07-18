"""Regression tests for the final seven-family cassette gate."""

from __future__ import annotations

import json

import pytest

from tests.llm.models import BENCHMARK_MODELS, MODEL_PROFILES
from tests.llm.runner import LLMTestRunner


def test_release_gate_contains_exactly_seven_distinct_model_families() -> None:
    assert len(BENCHMARK_MODELS) == 7
    assert len({MODEL_PROFILES[model].family for model in BENCHMARK_MODELS}) == 7
    assert "openai/gpt-5-nano" not in MODEL_PROFILES
    assert "z-ai/glm-4.7-flash" not in MODEL_PROFILES


def test_runner_rejects_review_codes_routed_to_stops() -> None:
    runner = LLMTestRunner(client=None)
    payload = json.dumps(
        {
            "status": "STOPPED",
            "stops": ["REVIEW_01", "REVIEW_09"],
            "reviews": [],
        }
    )

    with pytest.raises(ValueError, match="non-STOP codes in stops"):
        runner.parse_decision(payload)


def test_runner_rejects_status_inconsistent_with_stop_presence() -> None:
    runner = LLMTestRunner(client=None)
    payload = json.dumps(
        {
            "status": "STOPPED",
            "stops": [],
            "reviews": ["REVIEW_01"],
        }
    )

    with pytest.raises(ValueError, match="inconsistent with stops"):
        runner.parse_decision(payload)
