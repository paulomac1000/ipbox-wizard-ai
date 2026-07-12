"""
Cassette model for VCR recordings.

Cassette = recorded conversation turn(s) with metadata.
Format: YAML (readable, git-diff friendly, committed to repo).
Supports multi-turn for future wizard-mode compatibility.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml


@dataclass
class CassetteMeta:
    """Metadata for a cassette recording."""
    scenario_id: str
    scenario_name: str
    provider: str
    model: str
    fingerprint: str
    recorded_at: str = ""  # ISO 8601
    recording_duration_seconds: float = 0
    prompt_tokens_estimate: int = 0
    response_tokens_estimate: int = 0
    algorithm_hash: str = ""
    cassette_format_version: int = 2

    def __post_init__(self):
        if not self.recorded_at:
            self.recorded_at = datetime.now(UTC).isoformat()


@dataclass
class CassetteTurn:
    """Single conversation turn (request → response)."""
    role: str = "user"  # "user" or "assistant"
    prompt: str = ""
    response: str = ""
    prompt_hash: str = ""
    request_hash: str = ""
    system_prompt_hash: str = ""


@dataclass
class Cassette:
    """Complete cassette with metadata and turns."""
    meta: CassetteMeta
    turns: list[CassetteTurn] = field(default_factory=list)

    # Pre-parsed results (cached for fast test access)
    parsed_result_yaml: dict | None = None
    parsed_classifications: dict | None = None
    parsed_monthly_W: dict | None = None
    parsed_tests: dict | None = None
    parsed_stops_reviews: dict | None = None

    def to_yaml(self) -> str:
        """Serialize cassette to YAML string."""
        data = {
            "meta": asdict(self.meta),
            "turns": [asdict(t) for t in self.turns],
        }

        # Add parsed data if available
        if self.parsed_result_yaml:
            data["parsed"] = {
                "result_yaml": self.parsed_result_yaml,
                "classifications": self.parsed_classifications,
                "monthly_W": self.parsed_monthly_W,
                "tests": self.parsed_tests,
                "stops_reviews": self.parsed_stops_reviews,
            }

        return yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            width=120,
            sort_keys=False,
        )

    def save(self, path: Path) -> None:
        """Save cassette to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_yaml(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Cassette:
        """Load cassette from file."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        meta = CassetteMeta(**data["meta"])
        turns = [CassetteTurn(**t) for t in data.get("turns", [])]

        parsed = data.get("parsed", {})

        return cls(
            meta=meta,
            turns=turns,
            parsed_result_yaml=parsed.get("result_yaml"),
            parsed_classifications=parsed.get("classifications"),
            parsed_monthly_W=parsed.get("monthly_W"),
            parsed_tests=parsed.get("tests"),
            parsed_stops_reviews=parsed.get("stops_reviews"),
        )

    @property
    def response(self) -> str:
        """Get response from first (or only) turn."""
        if self.turns:
            return self.turns[0].response
        return ""

    @property
    def is_valid(self) -> bool:
        """Check if cassette has a valid response."""
        return bool(self.response.strip())


# ============================================================================
# Manifest — index of all cassettes for quick lookup
# ============================================================================

@dataclass
class CassetteManifest:
    """Index of cassettes with fingerprints for quick validation."""
    entries: dict[str, dict[str, str]] = field(default_factory=dict)
    # {scenario_id: {"fingerprint": "...", "file": "...", "recorded_at": "..."}}

    def save(self, path: Path) -> None:
        """Save manifest to YAML file."""
        data = {
            "manifest_version": 1,
            "generated_at": datetime.now(UTC).isoformat(),
            "entries": self.entries,
        }
        path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> CassetteManifest:
        """Load manifest from file."""
        if not path.exists():
            return cls()
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(entries=data.get("entries", {}))

    def get_fingerprint(self, scenario_id: str) -> str | None:
        """Get fingerprint for scenario from manifest."""
        entry = self.entries.get(scenario_id)
        return entry["fingerprint"] if entry else None

    def update(
        self,
        scenario_id: str,
        fingerprint: str,
        filename: str,
    ) -> None:
        """Update or add entry to manifest."""
        self.entries[scenario_id] = {
            "fingerprint": fingerprint,
            "file": filename,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
