"""Versioned cassette and per-model manifest formats."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

CASSETTE_FORMAT_VERSION = 4
MANIFEST_FORMAT_VERSION = 2


@dataclass(frozen=True, slots=True)
class CassetteMeta:
    scenario_id: str
    scenario_name: str
    provider: str
    requested_model: str
    returned_model: str | None
    fingerprint: str
    request_hash: str
    recorded_at: str
    request_id: str | None
    finish_reason: str | None
    native_finish_reason: str | None
    system_fingerprint: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost: float | None
    recording_duration_seconds: float
    cassette_format_version: int = CASSETTE_FORMAT_VERSION


@dataclass(frozen=True, slots=True)
class Cassette:
    meta: CassetteMeta
    response: str
    parsed_response: dict[str, Any]

    def to_yaml(self) -> str:
        return yaml.safe_dump(
            {
                "meta": asdict(self.meta),
                "response": self.response,
                "parsed_response": self.parsed_response,
            },
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(self.to_yaml(), encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def load(cls, path: Path) -> Cassette:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Cassette {path} must be a mapping")
        meta_data = data.get("meta")
        if not isinstance(meta_data, dict):
            raise ValueError(f"Cassette {path} has no meta mapping")
        if meta_data.get("cassette_format_version") != CASSETTE_FORMAT_VERSION:
            raise ValueError(
                f"Unsupported cassette version {meta_data.get('cassette_format_version')!r}; "
                f"expected {CASSETTE_FORMAT_VERSION}"
            )
        meta = CassetteMeta(**meta_data)
        response = data.get("response")
        parsed = data.get("parsed_response")
        if not isinstance(response, str) or not response.strip():
            raise ValueError(f"Cassette {path} has an empty response")
        if not isinstance(parsed, dict):
            raise ValueError(f"Cassette {path} has no parsed response")
        return cls(meta=meta, response=response, parsed_response=parsed)


@dataclass(slots=True)
class CassetteManifest:
    model: str
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path, model: str) -> CassetteManifest:
        if not path.exists():
            return cls(model=model)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("manifest_format_version") != MANIFEST_FORMAT_VERSION:
            raise ValueError(f"Unsupported manifest version in {path}")
        if data.get("model") != model:
            raise ValueError(f"Manifest model mismatch in {path}")
        entries = data.get("entries")
        if not isinstance(entries, dict):
            raise ValueError(f"Manifest entries must be a mapping in {path}")
        return cls(model=model, entries=entries)

    def update(self, cassette: Cassette, filename: str) -> None:
        self.entries[cassette.meta.scenario_id] = {
            "file": filename,
            "fingerprint": cassette.meta.fingerprint,
            "request_hash": cassette.meta.request_hash,
            "recorded_at": cassette.meta.recorded_at,
            "returned_model": cassette.meta.returned_model,
            "cost": cassette.meta.cost,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "manifest_format_version": MANIFEST_FORMAT_VERSION,
            "model": self.model,
            "generated_at": datetime.now(UTC).isoformat(),
            "entries": dict(sorted(self.entries.items())),
        }
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        temporary.replace(path)
