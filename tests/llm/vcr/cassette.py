"""Versioned cassette and per-model manifest formats."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

CASSETTE_FORMAT_VERSION = 4
MANIFEST_FORMAT_VERSION = 3


def _meta_equal_without_calculated_at(ma: dict | None, mb: dict | None) -> bool:
    ma = ma or {}
    mb = mb or {}
    return all(ma.get(key) == mb.get(key) for key in set(ma) | set(mb) if key != "calculated_at")


def parsed_response_equal_ignoring_meta_timestamp(a: dict, b: dict) -> bool:
    if type(a) is not type(b):
        return False
    if a.keys() != b.keys():
        return False
    for key in a:
        if isinstance(a[key], dict):
            if key == "calculation_meta":
                if not _meta_equal_without_calculated_at(a[key], b[key]):
                    return False
                continue
            if not parsed_response_equal_ignoring_meta_timestamp(a[key], b[key]):
                return False
        elif isinstance(a[key], list):
            if len(a[key]) != len(b[key]):
                return False
            for value_a, value_b in zip(a[key], b[key], strict=False):
                if isinstance(value_a, dict | list):
                    if not parsed_response_equal_ignoring_meta_timestamp(value_a, value_b):
                        return False
                elif value_a != value_b:
                    return False
        elif a[key] != b[key]:
            return False
    return True


def _require_nonempty_text(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"cassette meta {name} must be a non-empty string")


def _require_optional_nonnegative_int(name: str, value: Any) -> None:
    if value is not None and (type(value) is not int or value < 0):
        raise ValueError(f"cassette meta {name} must be a non-negative integer or null")


def _require_nonnegative_finite_number(name: str, value: Any, *, optional: bool) -> None:
    if optional and value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"cassette meta {name} must be a finite non-negative number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"cassette meta {name} must be a finite non-negative number")


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

    def __post_init__(self) -> None:
        if type(self.cassette_format_version) is not int or (
            self.cassette_format_version != CASSETTE_FORMAT_VERSION
        ):
            raise ValueError(f"cassette_format_version must equal {CASSETTE_FORMAT_VERSION}")
        for name in (
            "scenario_id",
            "scenario_name",
            "provider",
            "requested_model",
            "returned_model",
            "fingerprint",
            "request_hash",
            "recorded_at",
            "finish_reason",
        ):
            _require_nonempty_text(name, getattr(self, name))
        if len(self.request_hash) != 64 or any(
            character not in "0123456789abcdef" for character in self.request_hash
        ):
            raise ValueError("cassette meta request_hash must be 64 lowercase hex characters")
        try:
            recorded = datetime.fromisoformat(self.recorded_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("cassette meta recorded_at must be ISO-8601") from exc
        if recorded.tzinfo is None:
            raise ValueError("cassette meta recorded_at must include a timezone")
        for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
            _require_optional_nonnegative_int(name, getattr(self, name))
        _require_nonnegative_finite_number("cost", self.cost, optional=True)
        _require_nonnegative_finite_number(
            "recording_duration_seconds",
            self.recording_duration_seconds,
            optional=False,
        )


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
        calculation_meta = cassette.parsed_response.get("calculation_meta")
        engine_hash = (
            calculation_meta.get("engine_source_hash")
            if isinstance(calculation_meta, dict)
            else None
        )
        if engine_hash is not None and (not isinstance(engine_hash, str) or len(engine_hash) != 64):
            raise ValueError("cassette calculation_meta has invalid engine_source_hash")
        self.entries[cassette.meta.scenario_id] = {
            "file": filename,
            "fingerprint": cassette.meta.fingerprint,
            "request_hash": cassette.meta.request_hash,
            "engine_source_hash": engine_hash,
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
