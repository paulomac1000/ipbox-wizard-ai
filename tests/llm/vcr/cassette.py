"""Canonical cassette and per-model manifest schemas."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

CASSETTE_TOP_LEVEL_FIELDS = frozenset({"meta", "response", "parsed_response"})
MANIFEST_TOP_LEVEL_FIELDS = frozenset({"model", "generated_at", "entries"})
MANIFEST_ENTRY_FIELDS = frozenset(
    {
        "file",
        "fingerprint",
        "request_hash",
        "engine_source_hash",
        "recorded_at",
        "returned_model",
        "cost",
    }
)


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


def _require_exact_fields(name: str, value: Mapping[str, Any], expected: frozenset[str]) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise ValueError(f"{name} fields mismatch; missing={missing}, extra={extra}")


def _require_nonempty_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _require_optional_text(name: str, value: Any) -> None:
    if value is not None:
        _require_nonempty_text(name, value)


def _require_sha256(name: str, value: Any) -> str:
    text = _require_nonempty_text(name, value)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")
    return text


def _require_fingerprint(value: Any) -> str:
    text = _require_nonempty_text("fingerprint", value)
    prefix = "canonical-source_"
    if not text.startswith(prefix):
        raise ValueError(f"fingerprint must start with {prefix!r}")
    _require_sha256("fingerprint digest", text.removeprefix(prefix))
    return text


def _require_timestamp(name: str, value: Any) -> str:
    text = _require_nonempty_text(name, value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone")
    return text


def _require_nonnegative_int(name: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _require_nonnegative_finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a finite non-negative number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return number


@dataclass(frozen=True, slots=True)
class CassetteMeta:
    scenario_id: str
    scenario_name: str
    provider: str
    requested_model: str
    returned_model: str
    fingerprint: str
    request_hash: str
    recorded_at: str
    request_id: str | None
    finish_reason: str
    native_finish_reason: str | None
    system_fingerprint: str | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    recording_duration_seconds: float

    def __post_init__(self) -> None:
        for name in (
            "scenario_id",
            "scenario_name",
            "provider",
            "requested_model",
            "returned_model",
        ):
            _require_nonempty_text(name, getattr(self, name))
        _require_fingerprint(self.fingerprint)
        _require_sha256("request_hash", self.request_hash)
        _require_timestamp("recorded_at", self.recorded_at)
        for name in ("request_id", "native_finish_reason", "system_fingerprint"):
            _require_optional_text(name, getattr(self, name))
        if self.finish_reason != "stop":
            raise ValueError("finish_reason must equal 'stop'")
        prompt = _require_nonnegative_int("prompt_tokens", self.prompt_tokens)
        completion = _require_nonnegative_int("completion_tokens", self.completion_tokens)
        total = _require_nonnegative_int("total_tokens", self.total_tokens)
        if prompt + completion != total:
            raise ValueError("total_tokens must equal prompt_tokens + completion_tokens")
        _require_nonnegative_finite_number("cost", self.cost)
        _require_nonnegative_finite_number(
            "recording_duration_seconds",
            self.recording_duration_seconds,
        )


@dataclass(frozen=True, slots=True)
class Cassette:
    meta: CassetteMeta
    response: str
    parsed_response: dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.response, str) or not self.response.strip():
            raise ValueError("cassette response must be a non-empty string")
        if not isinstance(self.parsed_response, dict):
            raise ValueError("cassette parsed_response must be a mapping")

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
        _require_exact_fields(f"Cassette {path}", data, CASSETTE_TOP_LEVEL_FIELDS)
        meta_data = data["meta"]
        if not isinstance(meta_data, dict):
            raise ValueError(f"Cassette {path} meta must be a mapping")
        expected_meta_fields = frozenset(CassetteMeta.__dataclass_fields__)
        _require_exact_fields(f"Cassette {path} meta", meta_data, expected_meta_fields)
        return cls(
            meta=CassetteMeta(**meta_data),
            response=data["response"],
            parsed_response=data["parsed_response"],
        )


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    file: str
    fingerprint: str
    request_hash: str
    engine_source_hash: str
    recorded_at: str
    returned_model: str
    cost: float

    def __post_init__(self) -> None:
        filename = _require_nonempty_text("manifest entry file", self.file)
        if Path(filename).name != filename or not filename.endswith(".yaml"):
            raise ValueError("manifest entry file must be a local YAML filename")
        if filename == "_manifest.yaml":
            raise ValueError("manifest entry cannot point to the manifest itself")
        _require_fingerprint(self.fingerprint)
        _require_sha256("manifest entry request_hash", self.request_hash)
        _require_sha256("manifest entry engine_source_hash", self.engine_source_hash)
        _require_timestamp("manifest entry recorded_at", self.recorded_at)
        _require_nonempty_text("manifest entry returned_model", self.returned_model)
        _require_nonnegative_finite_number("manifest entry cost", self.cost)

    @classmethod
    def from_mapping(cls, scenario_id: str, value: Any) -> ManifestEntry:
        if not isinstance(value, dict):
            raise ValueError(f"manifest entry {scenario_id!r} must be a mapping")
        _require_exact_fields(
            f"manifest entry {scenario_id!r}",
            value,
            MANIFEST_ENTRY_FIELDS,
        )
        entry = cls(**value)
        if Path(entry.file).stem != scenario_id:
            raise ValueError(f"manifest entry {scenario_id!r} file stem must equal the scenario id")
        return entry


@dataclass(slots=True)
class CassetteManifest:
    model: str
    entries: dict[str, ManifestEntry] = field(default_factory=dict)
    generated_at: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_text("manifest model", self.model)
        if self.generated_at is not None:
            _require_timestamp("manifest generated_at", self.generated_at)
        for scenario_id, entry in self.entries.items():
            _require_nonempty_text("manifest scenario id", scenario_id)
            if not isinstance(entry, ManifestEntry):
                raise ValueError(f"manifest entry {scenario_id!r} must be ManifestEntry")
            if Path(entry.file).stem != scenario_id:
                raise ValueError(
                    f"manifest entry {scenario_id!r} file stem must equal the scenario id"
                )
            if entry.returned_model != self.model:
                raise ValueError(
                    f"manifest entry {scenario_id!r} returned_model does not match manifest model"
                )

    @classmethod
    def load(cls, path: Path, model: str) -> CassetteManifest:
        if not path.exists():
            return cls(model=model)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Manifest {path} must be a mapping")
        _require_exact_fields(f"Manifest {path}", data, MANIFEST_TOP_LEVEL_FIELDS)
        if data["model"] != model:
            raise ValueError(f"Manifest model mismatch in {path}")
        _require_timestamp("manifest generated_at", data["generated_at"])
        raw_entries = data["entries"]
        if not isinstance(raw_entries, dict):
            raise ValueError(f"Manifest entries must be a mapping in {path}")
        entries: dict[str, ManifestEntry] = {}
        for raw_scenario_id, value in raw_entries.items():
            scenario_id = _require_nonempty_text("manifest scenario id", raw_scenario_id)
            if scenario_id != raw_scenario_id:
                raise ValueError("manifest scenario ids cannot contain surrounding whitespace")
            entries[scenario_id] = ManifestEntry.from_mapping(scenario_id, value)
        return cls(model=model, entries=entries, generated_at=data["generated_at"])

    def update(self, cassette: Cassette, filename: str) -> None:
        calculation_meta = cassette.parsed_response.get("calculation_meta")
        if not isinstance(calculation_meta, dict):
            raise ValueError("cassette parsed_response requires calculation_meta")
        engine_hash = calculation_meta.get("engine_source_hash")
        _require_sha256("cassette calculation_meta engine_source_hash", engine_hash)
        self.entries[cassette.meta.scenario_id] = ManifestEntry(
            file=filename,
            fingerprint=cassette.meta.fingerprint,
            request_hash=cassette.meta.request_hash,
            engine_source_hash=engine_hash,
            recorded_at=cassette.meta.recorded_at,
            returned_model=cassette.meta.returned_model,
            cost=cassette.meta.cost,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.now(UTC).isoformat()
        payload = {
            "model": self.model,
            "generated_at": generated_at,
            "entries": {
                scenario_id: asdict(entry) for scenario_id, entry in sorted(self.entries.items())
            },
        }
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        temporary.replace(path)
        self.generated_at = generated_at


def manifest_entry_errors(
    entry: ManifestEntry,
    cassette: Cassette,
    *,
    expected_file: str,
    expected_request_hash: str,
    expected_fingerprint: str,
    expected_engine_hash: str,
) -> list[str]:
    """Return every mismatch between one manifest entry and its cassette."""
    comparisons = (
        ("filename", entry.file, expected_file),
        ("request_hash", entry.request_hash, expected_request_hash),
        ("fingerprint", entry.fingerprint, expected_fingerprint),
        ("engine_source_hash", entry.engine_source_hash, expected_engine_hash),
        ("returned_model", entry.returned_model, cassette.meta.returned_model),
        ("recorded_at", entry.recorded_at, cassette.meta.recorded_at),
        ("cost", entry.cost, cassette.meta.cost),
    )
    return [
        f"manifest {name} mismatch" for name, actual, expected in comparisons if actual != expected
    ]
