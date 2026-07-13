"""Unit tests for the VCR (Virtual Cassette Recorder) system.
All cassettes created via tmp_path — never in repo's cassette directory."""

import hashlib
from pathlib import Path

import pytest

from tests.llm.vcr import VCRConfig, VCRMode, fingerprint_changed
from tests.llm.vcr.cassette import Cassette, CassetteMeta, CassetteTurn
from tests.llm.vcr.recorder import CassetteNotFoundError, VCRRecorder


def make_temp_cassette(tmp_path: Path, scenario_id: str = "test", prompt: str = "test prompt",
                       response: str = "test response", fingerprint: str = "fp_v1") -> Path:
    """Create a cassette in tmp_path and return its path."""
    root = tmp_path / "cassettes"
    model_dir = root / "test" / "test_model"
    model_dir.mkdir(parents=True, exist_ok=True)
    cassette_path = model_dir / f"{scenario_id}.yaml"
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    cassette = Cassette(
        meta=CassetteMeta(scenario_id=scenario_id, scenario_name=scenario_id,
                          provider="test", model="test", fingerprint=fingerprint),
        turns=[CassetteTurn(role="user", prompt=prompt, response=response, prompt_hash=prompt_hash)])
    cassette.save(cassette_path)
    return cassette_path


class TestVCRMode:
    @pytest.mark.unit
    @pytest.mark.P0
    def test_playback_needs_no_api_key(self):
        config = VCRConfig()
        config.mode = VCRMode.PLAYBACK
        assert not config.needs_api_key

    @pytest.mark.unit
    @pytest.mark.P0
    def test_record_needs_api_key(self):
        config = VCRConfig()
        config.mode = VCRMode.RECORD
        assert config.needs_api_key


class TestFingerprint:
    @pytest.mark.unit
    @pytest.mark.P1
    def test_fingerprint_changed_detects_difference(self):
        assert fingerprint_changed("abc", "def")

    @pytest.mark.unit
    @pytest.mark.P1
    def test_fingerprint_changed_same(self):
        assert not fingerprint_changed("same", "same")

    @pytest.mark.unit
    @pytest.mark.P1
    def test_different_prompts_different_hashes(self):
        h1 = hashlib.sha256(b"prompt1").hexdigest()[:16]
        h2 = hashlib.sha256(b"prompt2").hexdigest()[:16]
        assert h1 != h2


class TestCassette:
    @pytest.mark.unit
    @pytest.mark.P1
    def test_cassette_is_valid_with_response(self):
        turn = CassetteTurn(response="valid response")
        cassette = Cassette(meta=CassetteMeta(scenario_id="t", scenario_name="t",
                            provider="t", model="t", fingerprint="f"), turns=[turn])
        assert cassette.is_valid

    @pytest.mark.unit
    @pytest.mark.P1
    def test_cassette_not_valid_with_empty_response(self):
        turn = CassetteTurn(response="")
        cassette = Cassette(meta=CassetteMeta(scenario_id="t", scenario_name="t",
                            provider="t", model="t", fingerprint="f"), turns=[turn])
        assert not cassette.is_valid

    @pytest.mark.unit
    @pytest.mark.P1
    def test_cassette_has_request_hash_field(self):
        turn = CassetteTurn()
        assert hasattr(turn, "request_hash")
        assert turn.request_hash == ""

    @pytest.mark.unit
    @pytest.mark.P1
    def test_cassette_save_and_load(self, tmp_path):
        cassette_path = make_temp_cassette(tmp_path)
        loaded = Cassette.load(cassette_path)
        assert loaded.is_valid
        assert loaded.response == "test response"
        assert loaded.meta.scenario_id == "test"


class TestVCRRecorder:
    @pytest.mark.unit
    @pytest.mark.P1
    def test_missing_cassette_in_playback_raises_error(self, tmp_path):
        config = VCRConfig()
        config.mode = VCRMode.PLAYBACK
        config.cassettes_root = tmp_path / "cassettes"
        recorder = VCRRecorder(config)
        with pytest.raises(CassetteNotFoundError):
            recorder.get_or_record(
                scenario_id="nonexistent",
                scenario_path=Path("/nonexistent.yaml"),
                prompt="test",
                api_call_fn=lambda p: "response",
            )

    @pytest.mark.unit
    @pytest.mark.P1
    def test_model_collision_not_possible(self, tmp_path):
        """Two models with same scenario_id use separate files."""
        root = tmp_path / "cassettes"

        config_a = VCRConfig()
        config_a.cassettes_root = root
        config_a.model = "model_a"
        config_a.provider = "test"
        config_a.mode = VCRMode.RECORD
        recorder_a = VCRRecorder(config_a)
        resp_a = recorder_a.get_or_record(
            scenario_id="shared", scenario_path=Path(__file__),
            prompt="hello", api_call_fn=lambda p: "response_a",
        )

        config_b = VCRConfig()
        config_b.cassettes_root = root
        config_b.model = "model_b"
        config_b.provider = "test"
        config_b.mode = VCRMode.RECORD
        recorder_b = VCRRecorder(config_b)
        resp_b = recorder_b.get_or_record(
            scenario_id="shared", scenario_path=Path(__file__),
            prompt="hello", api_call_fn=lambda p: "response_b",
        )

        assert resp_a == "response_a"
        assert resp_b == "response_b"
        path_a = config_a.cassette_path("shared")
        path_b = config_b.cassette_path("shared")
        assert path_a != path_b
        assert path_a.exists()
        assert path_b.exists()

    @pytest.mark.unit
    @pytest.mark.P1
    def test_no_live_fallback_in_playback(self, tmp_path):
        """Playback without API key should fail, not call live API."""
        config = VCRConfig()
        config.cassettes_root = tmp_path / "cassettes"
        config.mode = VCRMode.PLAYBACK
        recorder = VCRRecorder(config)
        with pytest.raises(CassetteNotFoundError):
            recorder.get_or_record(
                scenario_id="nonexistent", scenario_path=Path(__file__),
                prompt="test",
                api_call_fn=lambda p: (_ for _ in ()).throw(
                    RuntimeError("live API called in playback")
                ),
            )

    @pytest.mark.unit
    @pytest.mark.P1
    def test_cassette_format_version_3_default(self, tmp_path):
        """New cassettes default to format_version=3."""
        cassette = Cassette(
            meta=CassetteMeta(scenario_id="t", scenario_name="t",
                              provider="t", model="t", fingerprint="f"),
            turns=[CassetteTurn()],
        )
        assert cassette.meta.cassette_format_version == 3
