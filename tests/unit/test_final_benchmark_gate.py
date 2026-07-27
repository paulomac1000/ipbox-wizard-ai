"""Regression tests for the final seven-family cassette gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.llm.models import BENCHMARK_MODELS, MODEL_PROFILES, ModelProfile
from tests.llm.output_schema import DECISION_JSON_SCHEMA
from tests.llm.runner import LLMTestRunner

ROOT = Path(__file__).resolve().parents[2]


def test_release_gate_contains_exactly_seven_distinct_model_families() -> None:
    assert len(BENCHMARK_MODELS) == 7
    assert len({MODEL_PROFILES[model].family for model in BENCHMARK_MODELS}) == 7
    assert "openai/gpt-5-nano" not in MODEL_PROFILES
    assert "z-ai/glm-4.7-flash" not in MODEL_PROFILES


def test_provider_transport_profiles_are_explicit_and_validated() -> None:
    claude = MODEL_PROFILES["anthropic/claude-haiku-4.5"]
    minimax = MODEL_PROFILES["minimax/minimax-m2.5"]

    assert claude.response_format_type == "json_schema"
    assert claude.strip_unique_items_for_transport is True
    assert minimax.response_format_type == "json_object"
    assert minimax.strip_unique_items_for_transport is False

    with pytest.raises(ValueError, match="response_format_type"):
        ModelProfile(model_id="x", label="x", family="x", response_format_type="invalid")
    with pytest.raises(ValueError, match="valid only with json_schema"):
        ModelProfile(
            model_id="x",
            label="x",
            family="x",
            response_format_type="json_object",
            strip_unique_items_for_transport=True,
        )


def test_transport_schema_compatibility_never_weakens_local_validation() -> None:
    local_schema = DECISION_JSON_SCHEMA["schema"]
    assert local_schema["properties"]["stops"]["uniqueItems"] is True
    assert local_schema["properties"]["reviews"]["uniqueItems"] is True

    transport = LLMTestRunner._transport_schema(strip_unique=True)
    transport_properties = transport["schema"]["properties"]
    assert "uniqueItems" not in transport_properties["stops"]
    assert "uniqueItems" not in transport_properties["reviews"]

    # Building a provider-compatible copy must never mutate the local source of truth.
    assert local_schema["properties"]["stops"]["uniqueItems"] is True
    assert local_schema["properties"]["reviews"]["uniqueItems"] is True

    nested = {"uniqueItems": True, "items": [{"properties": {"x": {"uniqueItems": True}}}]}
    LLMTestRunner._remove_schema_keyword(nested, "uniqueItems")
    assert nested == {"items": [{"properties": {"x": {}}}]}


def test_authoritative_contract_documents_match_the_executable_protocol() -> None:
    for relative_path in (
        "ipbox_algorytm.md",
        ".agents/onboarding.md",
        "examples/przykladowy_prompt_startowy.md",
    ):
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "expected_decision" in text, relative_path
        assert "active_rules" not in text, relative_path


def test_runner_rejects_review_codes_routed_to_stops_at_schema_boundary() -> None:
    runner = LLMTestRunner(client=None)
    payload = json.dumps(
        {
            "status": "STOPPED",
            "stops": ["REVIEW_01", "REVIEW_09"],
            "reviews": [],
        }
    )

    with pytest.raises(ValueError, match="decision does not match strict schema"):
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
