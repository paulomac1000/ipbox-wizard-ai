from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tests.llm.client import LLMClient, LLMResponse
from tests.llm.models import BENCHMARK_MODELS, get_model_profile
from tests.llm.request_spec import LLMRequestSpec
from tests.llm.vcr.cassette import Cassette, CassetteManifest
from tests.llm.vcr.config import VCRConfig
from tests.llm.vcr.recorder import (
    CassetteMissingError,
    CassetteStaleError,
    RecordingRejectedError,
    VCRRecorder,
)


def response(content='{"ok":true}', finish="stop") -> LLMResponse:
    return LLMResponse(
        content=content,
        request_id="req",
        requested_model="google/gemini-3.5-flash",
        returned_model="google/gemini-3.5-flash",
        finish_reason=finish,
        native_finish_reason="STOP",
        system_fingerprint="fp",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        cost=0.01,
    )


def spec(model="google/gemini-3.5-flash") -> LLMRequestSpec:
    return LLMRequestSpec(
        provider="openrouter",
        model=model,
        system_prompt="system",
        user_prompt="user",
        temperature=None,
        max_tokens=100,
        response_format={"type": "json_object"},
        reasoning={"effort": "minimal"},
    )


def scenario_file(tmp_path: Path) -> tuple[dict, Path]:
    scenario = {"meta": {"id": "s", "name": "S"}, "input": {}, "assertions": {"x": True}}
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump(scenario), encoding="utf-8")
    return scenario, path


def set_config_env(monkeypatch, tmp_path: Path, mode="playback", model="google/gemini-3.5-flash"):
    monkeypatch.setenv("VCR_MODE", mode)
    monkeypatch.setenv("LLM_MODEL", model)
    monkeypatch.setenv("VCR_CASSETTES_ROOT", str(tmp_path / "cassettes"))
    monkeypatch.setenv("VCR_REJECTED_ROOT", str(tmp_path / "rejected"))


def test_model_profiles_are_three_providers() -> None:
    assert BENCHMARK_MODELS == (
        "google/gemini-3.5-flash",
        "openai/gpt-5-mini",
        "anthropic/claude-haiku-4.5",
    )
    assert get_model_profile("openai/gpt-5-mini").reasoning == {"effort": "minimal"}
    with pytest.raises(ValueError):
        get_model_profile("bad")


def test_request_hash_changes_for_every_material_field() -> None:
    a = spec()
    assert a.request_hash() == spec().request_hash()
    # Build an otherwise identical request with one changed field.
    b = LLMRequestSpec(
        provider=a.provider,
        model=a.model,
        system_prompt=a.system_prompt,
        user_prompt="different",
        temperature=a.temperature,
        max_tokens=a.max_tokens,
        response_format=a.response_format,
        provider_preferences=a.provider_preferences,
        seed=a.seed,
        reasoning=a.reasoning,
    )
    assert a.request_hash() != b.request_hash()
    assert a.api_payload()["reasoning"] == {"effort": "minimal"}


def test_playback_missing_never_calls_api(monkeypatch, tmp_path) -> None:
    set_config_env(monkeypatch, tmp_path)
    scenario, path = scenario_file(tmp_path)
    called = False

    def api(_):
        nonlocal called
        called = True
        return response()

    with pytest.raises(CassetteMissingError):
        VCRRecorder(VCRConfig()).get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=spec(),
            api_call=api,
            validate_response=lambda content: json.loads(content),
        )
    assert called is False


def test_record_then_offline_playback(monkeypatch, tmp_path) -> None:
    set_config_env(monkeypatch, tmp_path, "record")
    scenario, path = scenario_file(tmp_path)
    recorder = VCRRecorder(VCRConfig())
    live, parsed = recorder.get_or_record(
        scenario=scenario,
        scenario_path=path,
        request=spec(),
        api_call=lambda _: response(),
        validate_response=lambda content: json.loads(content),
    )
    assert parsed == {"ok": True}
    assert recorder.config.cassette_path("s").exists()
    assert recorder.config.manifest_path.exists()
    monkeypatch.setenv("VCR_MODE", "playback")
    playback, parsed2 = VCRRecorder(VCRConfig()).get_or_record(
        scenario=scenario,
        scenario_path=path,
        request=spec(),
        api_call=None,
        validate_response=lambda content: json.loads(content),
    )
    assert playback.content == live.content
    assert parsed2 == parsed


def test_playback_detects_stale_request(monkeypatch, tmp_path) -> None:
    test_record_then_offline_playback(monkeypatch, tmp_path)
    scenario, path = scenario_file(tmp_path)
    with pytest.raises(CassetteStaleError):
        VCRRecorder(VCRConfig()).get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=LLMRequestSpec(
                provider="openrouter",
                model="google/gemini-3.5-flash",
                system_prompt="s",
                user_prompt="changed",
                temperature=None,
                max_tokens=100,
                response_format={"type": "json_object"},
                reasoning={"effort": "minimal"},
            ),
            api_call=None,
            validate_response=lambda content: json.loads(content),
        )


def test_record_rejects_invalid_or_truncated_response(monkeypatch, tmp_path) -> None:
    set_config_env(monkeypatch, tmp_path, "record")
    scenario, path = scenario_file(tmp_path)
    recorder = VCRRecorder(VCRConfig())
    with pytest.raises(RecordingRejectedError):
        recorder.get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=spec(),
            api_call=lambda _: response("not json"),
            validate_response=json.loads,
        )
    assert not recorder.config.cassette_path("s").exists()
    assert (recorder.config.rejected_root / recorder.config.model_slug / "s.json").exists()
    with pytest.raises(RecordingRejectedError):
        recorder.get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=spec(),
            api_call=lambda _: response(finish="length"),
            validate_response=json.loads,
        )


def test_cassette_and_manifest_reject_bad_versions(tmp_path) -> None:
    path = tmp_path / "c.yaml"
    path.write_text("meta: {}\nresponse: x\nparsed_response: {}\n", encoding="utf-8")
    with pytest.raises((TypeError, ValueError)):
        Cassette.load(path)
    manifest = tmp_path / "m.yaml"
    manifest.write_text("manifest_format_version: 1\nmodel: x\nentries: {}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        CassetteManifest.load(manifest, "x")


def test_vcr_config_model_only_path(monkeypatch, tmp_path) -> None:
    set_config_env(monkeypatch, tmp_path, model="anthropic/claude-haiku-4.5")
    config = VCRConfig()
    assert config.model_directory.name == "anthropic_claude_haiku_4_5"
    assert "openrouter" not in str(config.model_directory.relative_to(config.cassettes_root))


def test_client_requires_key_and_rejects_provider(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError):
        LLMClient()
    monkeypatch.setenv("LLM_PROVIDER", "direct")
    with pytest.raises(ValueError):
        LLMClient(require_api_key=False)
