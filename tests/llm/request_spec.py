"""Canonical request identity for VCR integrity."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


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

    def canonical_dict(self) -> dict[str, Any]:
        """Return a stable representation including omitted optional fields."""
        return asdict(self)

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
            "response_format": self.response_format,
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.reasoning is not None:
            payload["reasoning"] = self.reasoning
        if self.provider_preferences is not None:
            payload["provider"] = self.provider_preferences
        if self.seed is not None:
            payload["seed"] = self.seed
        return payload
