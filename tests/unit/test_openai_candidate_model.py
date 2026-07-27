"""Contract tests for recording OpenAI GPT-5 Mini before release-gate promotion."""

from __future__ import annotations

from pathlib import Path

from tests.llm.models import (
    BENCHMARK_MODELS,
    CANDIDATE_MODELS,
    SUPPORTED_MODELS,
    get_model_profile,
    model_slug,
)
from tests.llm.runner import LLMTestRunner
from tests.llm.vcr.config import VCRConfig

ROOT = Path(__file__).resolve().parents[2]
OPENAI_MODEL = "openai/gpt-5-mini"


def test_openai_model_is_supported_but_not_claimed_before_cassettes_exist() -> None:
    assert CANDIDATE_MODELS == (OPENAI_MODEL,)
    assert OPENAI_MODEL in SUPPORTED_MODELS
    assert OPENAI_MODEL not in BENCHMARK_MODELS

    profile = get_model_profile(OPENAI_MODEL)
    assert profile.label == "OpenAI GPT-5 Mini"
    assert profile.family == "OpenAI GPT"
    assert profile.temperature is None
    assert profile.reasoning == {"effort": "minimal"}
    assert profile.response_format_type == "json_schema"
    assert model_slug(OPENAI_MODEL) == "openai_gpt_5_mini"


def test_openai_transport_uses_strict_schema_and_minimal_reasoning(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_MODEL", OPENAI_MODEL)
    monkeypatch.setenv("VCR_MODE", "playback")

    config = VCRConfig()
    request = LLMTestRunner(client=None).request_spec("copy the decision", config)
    payload = request.api_payload()

    assert payload["model"] == OPENAI_MODEL
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["reasoning"] == {"effort": "minimal"}
    assert "temperature" not in payload


def test_paid_workflow_exposes_the_candidate_without_expanding_all_mode() -> None:
    workflow = (ROOT / ".github/workflows/llm-benchmark.yml").read_text(encoding="utf-8")
    assert f'- "{OPENAI_MODEL}"' in workflow
    assert "current release matrix; candidates run individually" in workflow
