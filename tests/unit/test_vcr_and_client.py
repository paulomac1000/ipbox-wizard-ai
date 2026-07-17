from __future__ import annotations

import json
from dataclasses import replace
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
        requested_model="google/gemini-3-flash-preview",
        returned_model="google/gemini-3-flash-preview",
        finish_reason=finish,
        native_finish_reason="STOP",
        system_fingerprint="fp",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        cost=0.01,
    )


def spec(model="google/gemini-3-flash-preview") -> LLMRequestSpec:
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


def set_config_env(
    monkeypatch, tmp_path: Path, mode="playback", model="google/gemini-3-flash-preview"
):
    monkeypatch.setenv("VCR_MODE", mode)
    monkeypatch.setenv("LLM_MODEL", model)
    monkeypatch.setenv("VCR_CASSETTES_ROOT", str(tmp_path / "cassettes"))
    monkeypatch.setenv("VCR_REJECTED_ROOT", str(tmp_path / "rejected"))


def record_valid_cassette(monkeypatch, tmp_path: Path) -> tuple[dict, Path, VCRRecorder]:
    set_config_env(monkeypatch, tmp_path, "record")
    scenario, path = scenario_file(tmp_path)
    recorder = VCRRecorder(VCRConfig())
    recorder.get_or_record(
        scenario=scenario,
        scenario_path=path,
        request=spec(),
        api_call=lambda _: response(),
        validate_response=lambda content: json.loads(content),
    )
    return scenario, path, recorder


def test_model_profiles_cover_nine_distinct_families() -> None:
    assert BENCHMARK_MODELS == (
        "google/gemini-3-flash-preview",
        "openai/gpt-5-nano",
        "anthropic/claude-haiku-4.5",
        "deepseek/deepseek-chat-v3.1",
        "minimax/minimax-m2.5",
        "moonshotai/kimi-k2.5",
        "z-ai/glm-4.7-flash",
        "qwen/qwen3.5-flash-02-23",
        "mistralai/ministral-3b-2512",
    )
    assert len({get_model_profile(model).family for model in BENCHMARK_MODELS}) == 9
    assert get_model_profile("openai/gpt-5-nano").reasoning == {"effort": "minimal"}
    assert all(
        get_model_profile(model).response_format_type == "json_schema" for model in BENCHMARK_MODELS
    )
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


def test_playback_rejects_incomplete_finish_reason(monkeypatch, tmp_path) -> None:
    scenario, path, recorder = record_valid_cassette(monkeypatch, tmp_path)
    cassette_path = recorder.config.cassette_path("s")
    cassette = Cassette.load(cassette_path)
    Cassette(
        meta=replace(cassette.meta, finish_reason="length"),
        response=cassette.response,
        parsed_response=cassette.parsed_response,
    ).save(cassette_path)

    monkeypatch.setenv("VCR_MODE", "playback")
    with pytest.raises(CassetteStaleError, match="finish_reason"):
        VCRRecorder(VCRConfig()).get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=spec(),
            api_call=None,
            validate_response=json.loads,
        )


def test_playback_rejects_returned_model_substitution(monkeypatch, tmp_path) -> None:
    scenario, path, recorder = record_valid_cassette(monkeypatch, tmp_path)
    cassette_path = recorder.config.cassette_path("s")
    cassette = Cassette.load(cassette_path)
    substituted = "provider/substituted-model"
    Cassette(
        meta=replace(cassette.meta, returned_model=substituted),
        response=cassette.response,
        parsed_response=cassette.parsed_response,
    ).save(cassette_path)
    manifest = CassetteManifest.load(recorder.config.manifest_path, recorder.config.model)
    manifest.entries["s"]["returned_model"] = substituted
    manifest.save(recorder.config.manifest_path)

    monkeypatch.setenv("VCR_MODE", "playback")
    with pytest.raises(CassetteStaleError, match="returned_model"):
        VCRRecorder(VCRConfig()).get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=spec(),
            api_call=None,
            validate_response=json.loads,
        )


def test_record_mode_reuses_valid_cassette_without_calling_api(monkeypatch, tmp_path) -> None:
    scenario, path, recorder = record_valid_cassette(monkeypatch, tmp_path)
    cassette_path = recorder.config.cassette_path("s")
    original = cassette_path.read_bytes()
    called = False

    def api(_):
        nonlocal called
        called = True
        return response(content='{"ok":false}')

    played, parsed = VCRRecorder(VCRConfig()).get_or_record(
        scenario=scenario,
        scenario_path=path,
        request=spec(),
        api_call=api,
        validate_response=json.loads,
    )
    assert called is False
    assert parsed == {"ok": True}
    assert played.content == '{"ok":true}'
    assert cassette_path.read_bytes() == original


def test_record_mode_refuses_to_overwrite_stale_cassette(monkeypatch, tmp_path) -> None:
    scenario, path, recorder = record_valid_cassette(monkeypatch, tmp_path)
    cassette_path = recorder.config.cassette_path("s")
    original = cassette_path.read_bytes()
    changed = LLMRequestSpec(
        provider="openrouter",
        model="google/gemini-3-flash-preview",
        system_prompt="system",
        user_prompt="changed",
        temperature=None,
        max_tokens=100,
        response_format={"type": "json_object"},
        reasoning={"effort": "minimal"},
    )
    called = False

    def api(_):
        nonlocal called
        called = True
        return response()

    with pytest.raises(CassetteStaleError, match="Refusing to overwrite"):
        VCRRecorder(VCRConfig()).get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=changed,
            api_call=api,
            validate_response=json.loads,
        )
    assert called is False
    assert cassette_path.read_bytes() == original


def test_playback_detects_stale_request(monkeypatch, tmp_path) -> None:
    scenario, path, _ = record_valid_cassette(monkeypatch, tmp_path)
    monkeypatch.setenv("VCR_MODE", "playback")
    with pytest.raises(CassetteStaleError):
        VCRRecorder(VCRConfig()).get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=LLMRequestSpec(
                provider="openrouter",
                model="google/gemini-3-flash-preview",
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


def test_request_spec_snapshots_mutable_inputs_and_returns_independent_payloads() -> None:
    response_format = {"type": "json_schema", "json_schema": {"strict": True}}
    reasoning = {"effort": "minimal"}
    request = LLMRequestSpec(
        provider="openrouter",
        model="google/gemini-3-flash-preview",
        system_prompt="system",
        user_prompt="user",
        max_tokens=100,
        response_format=response_format,
        reasoning=reasoning,
    )
    original_hash = request.request_hash()
    response_format["json_schema"]["strict"] = False
    reasoning["effort"] = "high"
    assert request.request_hash() == original_hash
    assert request.api_payload()["reasoning"] == {"effort": "minimal"}

    payload = request.api_payload()
    payload["response_format"]["json_schema"]["strict"] = False
    payload["reasoning"]["effort"] = "high"
    assert request.request_hash() == original_hash
    assert request.api_payload()["response_format"]["json_schema"]["strict"] is True


def test_none_mode_requires_complete_finish_reason(monkeypatch, tmp_path) -> None:
    set_config_env(monkeypatch, tmp_path, "none")
    scenario, path = scenario_file(tmp_path)
    with pytest.raises(RecordingRejectedError, match="finish_reason"):
        VCRRecorder(VCRConfig()).get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=spec(),
            api_call=lambda _: response(finish=None),
            validate_response=json.loads,
        )


def test_none_mode_rejects_returned_model_substitution(monkeypatch, tmp_path) -> None:
    set_config_env(monkeypatch, tmp_path, "none")
    scenario, path = scenario_file(tmp_path)
    substituted = replace(response(), returned_model="provider/substituted-model")
    with pytest.raises(RecordingRejectedError, match="returned_model"):
        VCRRecorder(VCRConfig()).get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=spec(),
            api_call=lambda _: substituted,
            validate_response=json.loads,
        )


def test_playback_rejects_tampered_parsed_response(monkeypatch, tmp_path) -> None:
    set_config_env(monkeypatch, tmp_path, "record")
    scenario, path = scenario_file(tmp_path)
    recorder = VCRRecorder(VCRConfig())
    recorder.get_or_record(
        scenario=scenario,
        scenario_path=path,
        request=spec(),
        api_call=lambda _: response(),
        validate_response=json.loads,
    )
    cassette_path = recorder.config.cassette_path("s")
    cassette = Cassette.load(cassette_path)
    Cassette(
        meta=cassette.meta,
        response=cassette.response,
        parsed_response={"ok": False},
    ).save(cassette_path)

    monkeypatch.setenv("VCR_MODE", "playback")
    with pytest.raises(CassetteStaleError, match="parsed_response"):
        VCRRecorder(VCRConfig()).get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=spec(),
            api_call=None,
            validate_response=json.loads,
        )


def test_client_retries_only_safe_transient_failures(monkeypatch) -> None:
    import requests

    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    client = LLMClient(require_api_key=False)
    sleeps = []
    monkeypatch.setattr("tests.llm.client.time.sleep", sleeps.append)

    response_429 = requests.Response()
    response_429.status_code = 429
    response_429.headers["Retry-After"] = "0"
    attempts = 0

    def transient(payload, timeout=180):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise requests.HTTPError(response=response_429)
        return response()

    monkeypatch.setattr(client, "call", transient)
    assert client.call_with_retry({"model": "x"}, retries=1).content
    assert attempts == 2
    assert sleeps == [0.0]

    response_500 = requests.Response()
    response_500.status_code = 500
    attempts = 0

    def permanent(payload, timeout=180):
        nonlocal attempts
        attempts += 1
        raise requests.HTTPError(response=response_500)

    monkeypatch.setattr(client, "call", permanent)
    with pytest.raises(requests.HTTPError):
        client.call_with_retry({"model": "x"}, retries=2, delay=0)
    assert attempts == 1


def test_client_does_not_retry_read_timeout_or_decode_failure(monkeypatch) -> None:
    import requests

    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    client = LLMClient(require_api_key=False)
    attempts = 0

    def read_timeout(payload, timeout=180):
        nonlocal attempts
        attempts += 1
        raise requests.ReadTimeout("response may have started")

    monkeypatch.setattr(client, "call", read_timeout)
    with pytest.raises(requests.ReadTimeout):
        client.call_with_retry({"model": "x"}, retries=2, delay=0)
    assert attempts == 1

    attempts = 0

    def decode_failure(payload, timeout=180):
        nonlocal attempts
        attempts += 1
        raise ValueError("invalid JSON")

    monkeypatch.setattr(client, "call", decode_failure)
    with pytest.raises(ValueError, match="invalid JSON"):
        client.call_with_retry({"model": "x"}, retries=2, delay=0)
    assert attempts == 1


def test_vcr_precommit_rejects_incomplete_or_tampered_payload(monkeypatch, tmp_path) -> None:
    from scripts.vcr_precommit import cassette_payload_errors

    _, _, recorder = record_valid_cassette(monkeypatch, tmp_path)
    cassette = Cassette.load(recorder.config.cassette_path("s"))
    assert cassette_payload_errors(cassette, {"ok": True}) == []

    incomplete = Cassette(
        meta=replace(cassette.meta, finish_reason=None),
        response=cassette.response,
        parsed_response=cassette.parsed_response,
    )
    assert any(
        "finish_reason" in error for error in cassette_payload_errors(incomplete, {"ok": True})
    )
    assert any(
        "parsed_response" in error for error in cassette_payload_errors(cassette, {"ok": False})
    )
    substituted = Cassette(
        meta=replace(cassette.meta, returned_model="provider/substituted-model"),
        response=cassette.response,
        parsed_response=cassette.parsed_response,
    )
    assert any(
        "returned_model" in error
        for error in cassette_payload_errors(
            substituted, {"ok": True}, "google/gemini-3-flash-preview"
        )
    )


def test_vcr_precommit_detects_orphan_cassette_files(tmp_path) -> None:
    from scripts.vcr_precommit import orphan_cassette_ids

    (tmp_path / "known.yaml").write_text("x", encoding="utf-8")
    (tmp_path / "orphan.yaml").write_text("x", encoding="utf-8")
    (tmp_path / "_manifest.yaml").write_text("x", encoding="utf-8")
    assert orphan_cassette_ids(tmp_path, {"known"}) == {"orphan"}


def test_recording_scripts_fail_closed_and_offer_no_force_override() -> None:
    import subprocess
    import sys

    root = Path(__file__).parents[2]
    process = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/record_model.py"),
            "--model",
            "google/gemini-3-flash-preview",
            "--force",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 2
    assert "unrecognized arguments: --force" in process.stderr
    shell = (root / "scripts/record_all_models.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in shell


def test_workflows_harden_checkout_and_shell_inputs() -> None:
    root = Path(__file__).parents[2]
    deterministic = (root / ".github/workflows/deterministic-ci.yml").read_text(encoding="utf-8")
    paid = (root / ".github/workflows/llm-benchmark.yml").read_text(encoding="utf-8")
    assert "persist-credentials: false" in deterministic
    assert "persist-credentials: false" in paid
    assert "BENCHMARK_MODEL: ${{ inputs.model }}" in paid
    assert "MAX_COST_USD: ${{ inputs.max-cost-usd }}" in paid
    assert 'if [ "${{ inputs.model }}"' not in paid


def test_record_model_refuses_to_overwrite_stale_cassette(monkeypatch, tmp_path) -> None:
    import sys

    import scripts.record_model as record_model

    scenario_dir = tmp_path / "scenarios"
    cassette_root = tmp_path / "cassettes"
    scenario_dir.mkdir()
    (scenario_dir / "01_case.yaml").write_text("meta: {id: 01_case}\n", encoding="utf-8")
    model = "google/gemini-3-flash-preview"
    cassette = cassette_root / record_model.slug(model) / "01_case.yaml"
    cassette.parent.mkdir(parents=True)
    cassette.write_text("do-not-overwrite", encoding="utf-8")

    calls = []
    monkeypatch.setattr(record_model, "SCENARIO_DIR", scenario_dir)
    monkeypatch.setattr(record_model, "CASSETTE_ROOT", cassette_root)
    monkeypatch.setattr(record_model, "run", lambda command, env: calls.append(command) or 1)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setattr(sys, "argv", ["record_model.py", "--model", model])

    assert record_model.main() == 1
    assert len(calls) == 1
    assert "--vcr-mode=playback" in calls[0]
    assert cassette.read_text(encoding="utf-8") == "do-not-overwrite"


def test_pytest_scenario_option_filters_collection() -> None:
    import subprocess
    import sys

    root = Path(__file__).parents[2]
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/llm/test_scenarios.py",
            "--collect-only",
            "-q",
            "--scenario",
            "44_mix_revenue_key_kis",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    assert "1 test collected" in process.stdout
    assert "44_mix_revenue_key_kis" in process.stdout


def test_pytest_scenario_option_rejects_no_match() -> None:
    import subprocess
    import sys

    root = Path(__file__).parents[2]
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/llm/test_scenarios.py",
            "--collect-only",
            "-q",
            "--scenario",
            "definitely_missing_scenario",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode != 0
    assert "matched no scenarios" in process.stdout + process.stderr


def test_runner_rejects_markdown_fenced_json() -> None:
    from tests.llm.runner import LLMTestRunner

    with pytest.raises(ValueError, match="pure JSON"):
        LLMTestRunner(None).parse_decision(
            '```json\n{"status":"FINAL","stops":[],"reviews":[]}\n```'
        )


def test_cassette_requires_explicit_format_version(tmp_path) -> None:
    path = tmp_path / "unversioned.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "meta": {
                    "scenario_id": "s",
                    "scenario_name": "S",
                    "provider": "openrouter",
                    "requested_model": "google/gemini-3-flash-preview",
                    "returned_model": "google/gemini-3-flash-preview",
                    "fingerprint": "f",
                    "request_hash": "h",
                    "recorded_at": "2026-01-01T00:00:00+00:00",
                    "request_id": "r",
                    "finish_reason": "stop",
                    "native_finish_reason": "STOP",
                    "system_fingerprint": None,
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                    "cost": 0.0,
                    "recording_duration_seconds": 0.1,
                },
                "response": '{"ok":true}',
                "parsed_response": {"ok": True},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unsupported cassette version None"):
        Cassette.load(path)


def test_record_rejects_provider_model_substitution(monkeypatch, tmp_path) -> None:
    set_config_env(monkeypatch, tmp_path, "record")
    scenario, path = scenario_file(tmp_path)
    substituted = replace(response(), returned_model="provider/other-model")
    with pytest.raises(RecordingRejectedError, match="does not match requested"):
        VCRRecorder(VCRConfig()).get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=spec(),
            api_call=lambda _: substituted,
            validate_response=json.loads,
        )


def test_policy_detects_unexpected_model_directory(tmp_path) -> None:
    from scripts.check_cassette_policy import unexpected_model_directories

    (tmp_path / "unexpected_model").mkdir()
    assert unexpected_model_directories(tmp_path) == {"unexpected_model"}


def test_benchmark_scenario_ids_require_filename_identity(tmp_path, monkeypatch) -> None:
    import scripts.benchmark_report as report

    root = tmp_path
    scenario_dir = root / "tests/llm/scenarios"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "filename.yaml").write_text("meta: {id: different}\n", encoding="utf-8")
    monkeypatch.setattr(report, "ROOT", root)
    with pytest.raises(ValueError, match="must equal filename stem"):
        report.scenario_ids_from_yaml()


def test_paid_entry_points_include_shell_gate_and_make_record_depends_on_test() -> None:
    root = Path(__file__).parents[2]
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/llm-benchmark.yml").read_text(encoding="utf-8")
    assert "record: test" in makefile
    assert 'bash -n "$$script"' in makefile
    assert 'bash -n "$script"' in workflow
