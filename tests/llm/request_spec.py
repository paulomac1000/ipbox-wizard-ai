"""LLMRequestSpec — immutable specification of a complete LLM request."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMRequestSpec:
    provider: str = "openrouter"
    model: str = "google/gemini-3.5-flash"
    system_prompt: str = ""
    user_prompt: str = ""
    temperature: float = 0.0
    max_tokens: int = 16000
    response_format: dict | None = None
    schema: dict | None = None
    json_schema: dict | None = None
    schema_version: str | None = None
    provider_preferences: dict | None = None
    seed: int | None = None
    reasoning_settings: dict | None = None

    def compute_hash(self) -> str:
        """Canonical JSON serialization for request_hash."""
        payload = json.dumps(
            dataclasses.asdict(self),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
