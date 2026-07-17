"""Canonical request identity for VCR integrity."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def _freeze_json(value: Any) -> Any:
    """Recursively snapshot JSON-compatible values into immutable containers."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    """Return an independent JSON-compatible copy of an immutable snapshot."""
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class LLMRequestSpec:
    provider: str
    model: str
    system_prompt: str
    user_prompt: str
    max_tokens: int
    response_format: dict[str, Any]
    temperature: float | None = None
    reasoning: dict[str, Any] | None = None
    provider_preferences: dict[str, Any] | None = None
    seed: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "response_format", _freeze_json(self.response_format))
        object.__setattr__(
            self,
            "reasoning",
            None if self.reasoning is None else _freeze_json(self.reasoning),
        )
        object.__setattr__(
            self,
            "provider_preferences",
            (
                None
                if self.provider_preferences is None
                else _freeze_json(self.provider_preferences)
            ),
        )

    def canonical_dict(self) -> dict[str, Any]:
        """Return a stable, independent representation including optional fields."""
        return {
            "provider": self.provider,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "max_tokens": self.max_tokens,
            "response_format": _thaw_json(self.response_format),
            "temperature": self.temperature,
            "reasoning": _thaw_json(self.reasoning),
            "provider_preferences": _thaw_json(self.provider_preferences),
            "seed": self.seed,
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def request_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def api_payload(self) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": self.user_prompt})
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "response_format": _thaw_json(self.response_format),
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.reasoning is not None:
            payload["reasoning"] = _thaw_json(self.reasoning)
        if self.provider_preferences is not None:
            payload["provider"] = _thaw_json(self.provider_preferences)
        if self.seed is not None:
            payload["seed"] = self.seed
        return payload
