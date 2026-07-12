"""
VCR Configuration — modes and environment variables.

Defines how VCR behaves: playback, auto, record, or none.
"""

from __future__ import annotations

from enum import Enum
from os import environ
from pathlib import Path


class VCRMode(Enum):
    """VCR operating modes."""

    PLAYBACK = "playback"
    # Always use cassettes. Fail if cassette missing or stale.
    # Default for CI/CD (zero API cost).

    AUTO = "auto"
    # Use cassette if exists and valid (fingerprint match + not stale).
    # Otherwise record new cassette.
    # Default for local development.

    RECORD = "record"
    # Always record (overwrite existing cassettes).
    # Use after algorithm/model changes.

    NONE = "none"
    # Bypass VCR — always call real API.
    # Use for debugging only.


class VCRConfig:
    """VCR configuration loaded from environment variables."""

    def __init__(self):
        self.mode = VCRMode(environ.get("VCR_MODE", "auto"))
        self.cassettes_dir = Path(
            environ.get(
                "VCR_CASSETTES_DIR",
                str(Path(__file__).parent / "cassettes"),
            )
        )
        self.manifest_path = self.cassettes_dir / "_manifest.yaml"

        # Staleness threshold in days (0 = never stale)
        self.max_age_days = int(environ.get("VCR_MAX_AGE_DAYS", "30"))

        # Whether to save full prompt in cassette (for debugging)
        self.save_full_prompt = environ.get(
            "VCR_SAVE_FULL_PROMPT", "false"
        ).lower() == "true"

        # LLM provider configuration
        self.provider = environ.get("LLM_PROVIDER", "google")
        self.model = environ.get("GEMINI_MODEL", "google/gemma-4-31b-it")

    @property
    def is_playback(self) -> bool:
        return self.mode == VCRMode.PLAYBACK

    @property
    def is_record(self) -> bool:
        return self.mode == VCRMode.RECORD

    @property
    def is_auto(self) -> bool:
        return self.mode == VCRMode.AUTO

    @property
    def is_none(self) -> bool:
        return self.mode == VCRMode.NONE

    @property
    def needs_api_key(self) -> bool:
        """Whether this mode requires an API key."""
        return self.mode in (VCRMode.AUTO, VCRMode.RECORD, VCRMode.NONE)

    def cassette_path(self, scenario_id: str) -> Path:
        """Get path to cassette for a given scenario."""
        # Include provider and model in filename for multi-provider support
        model_slug = self._model_slug()
        filename = f"{scenario_id}_{self.provider}_{model_slug}.yaml"
        return self.cassettes_dir / filename

    def _model_slug(self) -> str:
        """Create filesystem-safe model identifier."""
        return (
            self.model
            .replace("/", "_")
            .replace(".", "_")
            .replace("-", "_")
            [:60]
        )

    def __repr__(self) -> str:
        return (
            f"VCRConfig(mode={self.mode.value}, "
            f"cassettes={self.cassettes_dir}, "
            f"max_age={self.max_age_days}d)"
        )
