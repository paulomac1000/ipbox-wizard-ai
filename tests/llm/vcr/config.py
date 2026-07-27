"""Safe VCR configuration for LLM benchmark recordings."""

from __future__ import annotations

from enum import Enum
from os import environ
from pathlib import Path

from ..models import DEFAULT_MODEL, get_model_profile, model_slug


class VCRMode(str, Enum):
    PLAYBACK = "playback"
    RECORD = "record"
    NONE = "none"


class VCRConfig:
    def __init__(self) -> None:
        self.mode = VCRMode(environ.get("VCR_MODE", "playback"))
        self.provider = environ.get("LLM_PROVIDER", "openrouter")
        if self.provider != "openrouter":
            raise ValueError("Only OpenRouter is supported by the benchmark harness")
        self.model = environ.get("LLM_MODEL", DEFAULT_MODEL)
        self.profile = get_model_profile(self.model)
        self.cassettes_root = Path(
            environ.get(
                "VCR_CASSETTES_ROOT",
                str(Path(__file__).parent / "cassettes"),
            )
        )
        self.rejected_root = Path(environ.get("VCR_REJECTED_ROOT", "/tmp/ipbox_llm_rejected"))

    @property
    def model_slug(self) -> str:
        return model_slug(self.model)

    @property
    def model_directory(self) -> Path:
        return self.cassettes_root / self.model_slug

    @property
    def manifest_path(self) -> Path:
        return self.model_directory / "_manifest.yaml"

    def cassette_path(self, scenario_id: str) -> Path:
        return self.model_directory / f"{scenario_id}.yaml"

    @property
    def is_playback(self) -> bool:
        return self.mode is VCRMode.PLAYBACK

    @property
    def is_record(self) -> bool:
        return self.mode is VCRMode.RECORD

    @property
    def is_none(self) -> bool:
        return self.mode is VCRMode.NONE

    @property
    def needs_api_key(self) -> bool:
        return not self.is_playback
