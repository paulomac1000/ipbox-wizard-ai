"""Model profiles used by the provider-agnostic benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ModelProfile:
    model_id: str
    label: str
    max_tokens: int = 1024
    temperature: float | None = None
    reasoning: dict[str, Any] | None = None
    response_format_type: str = "json_schema"


MODEL_PROFILES: dict[str, ModelProfile] = {
    "google/gemini-3.5-flash": ModelProfile(
        model_id="google/gemini-3.5-flash",
        label="Google Gemini 3.5 Flash",
        reasoning={"effort": "minimal"},
    ),
    "openai/gpt-5-mini": ModelProfile(
        model_id="openai/gpt-5-mini",
        label="OpenAI GPT-5 Mini",
        reasoning={"effort": "minimal"},
    ),
    "anthropic/claude-haiku-4.5": ModelProfile(
        model_id="anthropic/claude-haiku-4.5",
        label="Anthropic Claude Haiku 4.5",
        temperature=0.0,
        response_format_type="json_object",
    ),
}

DEFAULT_MODEL = "google/gemini-3.5-flash"
BENCHMARK_MODELS = tuple(MODEL_PROFILES)


def get_model_profile(model_id: str) -> ModelProfile:
    """Return a supported benchmark profile and fail on silent substitutions."""
    try:
        return MODEL_PROFILES[model_id]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported benchmark model {model_id!r}. Use one of: {', '.join(MODEL_PROFILES)}"
        ) from exc
