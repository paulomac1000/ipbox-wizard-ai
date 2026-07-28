from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import ClassVar

import pytest

from python_helper.allocation_precision import audit_revenue_allocation
from scripts.local_env import load_local_env
from scripts.record_model import (
    PAID_RUN_CONFIRMATION,
    _cassette_root,
    _rejected_root,
    _require_paid_confirmation,
)
from tests.llm.client import LLMClient
from tests.llm.request_spec import LLMRequestSpec
from tests.llm.vcr.config import VCRConfig
from tests.llm.vcr.recorder import RecordingRejectedError, VCRRecorder

ROOT = Path(__file__).resolve().parents[2]
MODEL = "google/gemini-3-flash-preview"


def _request() -> LLMRequestSpec:
    return LLMRequestSpec(
        provider="openrouter",
        model=MODEL,
        system_prompt="system",
        user_prompt="user",
        temperature=None,
        max_tokens=100,
        response_format={"type": "json_object"},
        reasoning={"effort": "minimal"},
    )


def _scenario(tmp_path: Path) -> tuple[dict, Path]:
    scenario = {"meta": {"id": "paid-empty", "name": "Paid empty"}, "input": {}}
    path = tmp_path / "paid-empty.yaml"
    path.write_text("meta:\n  id: paid-empty\n  name: Paid empty\ninput: {}\n", encoding="utf-8")
    return scenario, path


def test_local_matrix_refuses_to_start_without_process_confirmation() -> None:
    env = os.environ.copy()
    env.pop("LLM_PAID_RUN_CONFIRMATION", None)
    result = subprocess.run(
        ["bash", "scripts/record_all_models.sh"],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "LLM_PAID_RUN_CONFIRMATION" in result.stderr
    assert "ruff" not in result.stdout


@pytest.mark.parametrize("value", [None, "", "yes", "RUN_PAID_BENCHMARK "])
def test_record_model_requires_exact_process_confirmation(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("LLM_PAID_RUN_CONFIRMATION", raising=False)
    else:
        monkeypatch.setenv("LLM_PAID_RUN_CONFIRMATION", value)
    with pytest.raises(SystemExit):
        _require_paid_confirmation(argparse.ArgumentParser())

    monkeypatch.setenv("LLM_PAID_RUN_CONFIRMATION", PAID_RUN_CONFIRMATION)
    _require_paid_confirmation(argparse.ArgumentParser())


def test_record_model_resolves_cassette_root_after_loading_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    expected = tmp_path / "custom-cassettes"
    env_path = tmp_path / ".env"
    env_path.write_text(f"VCR_CASSETTES_ROOT={expected}\n", encoding="utf-8")

    monkeypatch.delenv("VCR_CASSETTES_ROOT", raising=False)
    load_local_env(env_path)

    assert _cassette_root() == expected


def test_record_model_normalizes_relative_storage_roots_before_subprocess(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VCR_CASSETTES_ROOT", "relative/cassettes")
    monkeypatch.setenv("VCR_REJECTED_ROOT", "relative/rejected")

    assert _cassette_root() == (tmp_path / "relative/cassettes").resolve()
    assert _rejected_root(os.environ) == (tmp_path / "relative/rejected").resolve()


def test_record_model_rejects_empty_cassette_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VCR_CASSETTES_ROOT", "")
    with pytest.raises(ValueError, match="must not be empty"):
        _cassette_root()


def test_record_model_rejects_empty_rejected_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VCR_REJECTED_ROOT", "")
    with pytest.raises(ValueError, match="must not be empty"):
        _rejected_root(os.environ)


class _Response:
    headers: ClassVar[dict[str, str]] = {"x-request-id": "req-billed-empty"}

    @staticmethod
    def raise_for_status() -> None:
        return None

    @staticmethod
    def json() -> dict:
        return {
            "id": "req-billed-empty",
            "model": MODEL,
            "choices": [
                {
                    "finish_reason": "stop",
                    "native_finish_reason": "STOP",
                    "message": {"content": None, "refusal": "provider refused"},
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 0,
                "total_tokens": 10,
                "cost": 0.12,
            },
        }


def test_billed_empty_response_is_preserved_as_rejected_attempt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setattr("tests.llm.client.requests.post", lambda *args, **kwargs: _Response())

    billed = LLMClient().call({"model": MODEL})
    assert billed.content == ""
    assert billed.cost == pytest.approx(0.12)
    assert billed.provider_error == "non-string content; refusal='provider refused'"

    monkeypatch.setenv("VCR_MODE", "record")
    monkeypatch.setenv("LLM_MODEL", MODEL)
    monkeypatch.setenv("VCR_CASSETTES_ROOT", str(tmp_path / "cassettes"))
    monkeypatch.setenv("VCR_REJECTED_ROOT", str(tmp_path / "rejected"))
    scenario, scenario_path = _scenario(tmp_path)
    recorder = VCRRecorder(VCRConfig())

    with pytest.raises(RecordingRejectedError, match="content is empty"):
        recorder.get_or_record(
            scenario=scenario,
            scenario_path=scenario_path,
            request=_request(),
            api_call=lambda _: billed,
            validate_response=json.loads,
        )

    files = list((recorder.config.rejected_root / recorder.config.model_slug).glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["metadata"]["cost"] == pytest.approx(0.12)
    assert payload["metadata"]["provider_error"] == billed.provider_error
    assert payload["response"] == ""


@pytest.mark.parametrize("rounding_steps", [True, "100", 1.9, 0, -1])
def test_rounding_steps_must_be_a_real_positive_integer(rounding_steps: object) -> None:
    stream = {
        "month": "2025-01",
        "total_revenue": 100,
        "reported_ip_revenue": 50,
        "reported_non_ip_revenue": 50,
        "work_hours": 100,
        "non_ip_hours": 50,
        "invoice_percentage": 100,
        "w_method": "time_only",
        "rounding_steps": rounding_steps,
    }
    with pytest.raises(ValueError, match="rounding_steps must be a positive integer"):
        audit_revenue_allocation([stream])


def test_positive_integer_rounding_steps_remain_supported() -> None:
    stream = {
        "month": "2025-01",
        "total_revenue": 100,
        "reported_ip_revenue": 50,
        "reported_non_ip_revenue": 50,
        "work_hours": 100,
        "non_ip_hours": 50,
        "invoice_percentage": 100,
        "w_method": "time_only",
        "rounding_steps": 2,
    }
    assert audit_revenue_allocation([stream]) == []
