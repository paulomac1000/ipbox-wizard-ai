"""Contract tests for OpenAI GPT-5 Mini in the canonical benchmark matrix."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from python_helper.report_metadata import _canonical_source_files
from tests.llm.models import BENCHMARK_MODELS, MODEL_PROFILES, get_model_profile, model_slug
from tests.llm.runner import LLMTestRunner
from tests.llm.vcr.config import VCRConfig

ROOT = Path(__file__).resolve().parents[2]
OPENAI_MODEL = "openai/gpt-5-mini"


def test_openai_model_is_a_full_member_of_the_benchmark_matrix() -> None:
    assert OPENAI_MODEL in BENCHMARK_MODELS
    profile = get_model_profile(OPENAI_MODEL)
    assert profile is MODEL_PROFILES[OPENAI_MODEL]
    assert profile.label == "OpenAI GPT-5 Mini"
    assert profile.family == "OpenAI GPT"
    assert profile.temperature is None
    assert profile.reasoning == {"effort": "minimal"}
    assert profile.response_format_type == "json_schema"
    assert profile.strip_unique_items_for_transport is False
    assert model_slug(OPENAI_MODEL) == "openai_gpt_5_mini"


def test_model_registry_is_not_part_of_the_tax_engine_hash() -> None:
    canonical_paths = {relative for relative, _path in _canonical_source_files(ROOT)}
    assert "tests/llm/models.py" not in canonical_paths
    assert "tests/llm/runner.py" in canonical_paths
    assert "tests/llm/request_spec.py" in canonical_paths


def test_openai_transport_uses_the_common_strict_schema(monkeypatch) -> None:
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


def test_standard_recorder_refuses_openai_without_paid_confirmation(tmp_path) -> None:
    env = os.environ.copy()
    env.pop("LLM_PAID_RUN_CONFIRMATION", None)
    env["OPENROUTER_API_KEY"] = "test-key-must-not-be-used"
    env["VCR_REJECTED_ROOT"] = str(tmp_path / "rejected")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/record_model.py",
            "--model",
            OPENAI_MODEL,
            "--scenario",
            "01_basic_linear",
            "--max-cost-per-model-usd",
            "1",
            "--max-total-cost-usd",
            "1",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "paid recording requires an explicit process-level acknowledgement" in result.stderr


def test_paid_workflow_uses_the_standard_model_path() -> None:
    workflow = (ROOT / ".github/workflows/llm-benchmark.yml").read_text(encoding="utf-8")
    assert f'- "{OPENAI_MODEL}"' in workflow
    assert "full eight-family matrix" in workflow
    assert "python scripts/record_model.py" in workflow
    assert "python scripts/vcr_precommit.py --model" in workflow
    assert "python scripts/benchmark_report.py --model" in workflow
    assert "candidate_model" not in workflow
