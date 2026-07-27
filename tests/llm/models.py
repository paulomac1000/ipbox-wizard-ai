"""Model profiles used by the provider-agnostic diversity benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ModelProfile:
    """Exact provider request parameters for one benchmark model."""

    model_id: str
    label: str
    family: str
    max_tokens: int = 512
    temperature: float | None = None
    reasoning: dict[str, Any] | None = None
    response_format_type: str = "json_schema"
    strip_unique_items_for_transport: bool = False

    def __post_init__(self) -> None:
        if self.response_format_type not in {"json_schema", "json_object"}:
            raise ValueError(
                "response_format_type must be 'json_schema' or 'json_object', "
                f"got {self.response_format_type!r}"
            )
        if self.strip_unique_items_for_transport and self.response_format_type != "json_schema":
            raise ValueError(
                "strip_unique_items_for_transport is valid only with json_schema transport"
            )


MODEL_PROFILES: dict[str, ModelProfile] = {
    "google/gemini-3-flash-preview": ModelProfile(
        model_id="google/gemini-3-flash-preview",
        label="Google Gemini 3 Flash Preview",
        family="Google Gemini",
        reasoning={"effort": "minimal"},
    ),
    "anthropic/claude-haiku-4.5": ModelProfile(
        model_id="anthropic/claude-haiku-4.5",
        label="Anthropic Claude Haiku 4.5",
        family="Anthropic Claude",
        temperature=0.0,
        strip_unique_items_for_transport=True,
    ),
    "deepseek/deepseek-chat-v3.1": ModelProfile(
        model_id="deepseek/deepseek-chat-v3.1",
        label="DeepSeek",
        family="DeepSeek",
        temperature=0.0,
        reasoning={"enabled": False},
    ),
    "minimax/minimax-m2.5": ModelProfile(
        model_id="minimax/minimax-m2.5",
        label="MiniMax M2.5",
        family="MiniMax",
        temperature=0.0,
        response_format_type="json_object",
    ),
    "moonshotai/kimi-k2.5": ModelProfile(
        model_id="moonshotai/kimi-k2.5",
        label="Moonshot Kimi K2.5",
        family="Moonshot Kimi",
    ),
    "qwen/qwen3.5-flash-02-23": ModelProfile(
        model_id="qwen/qwen3.5-flash-02-23",
        label="Qwen 3.5 Flash",
        family="Qwen",
        temperature=0.0,
    ),
    "mistralai/mistral-small-24b-instruct-2501": ModelProfile(
        model_id="mistralai/mistral-small-24b-instruct-2501",
        label="Mistral Small 24B 2501",
        family="Mistral",
        temperature=0.0,
    ),
}

DEFAULT_MODEL = "google/gemini-3-flash-preview"
BENCHMARK_MODELS = tuple(MODEL_PROFILES)
EXPECTED_MODEL_COUNT = len(BENCHMARK_MODELS)


def model_slug(model_id: str) -> str:
    """Return the canonical filesystem slug for a benchmark model."""
    return model_id.replace("/", "_").replace(".", "_").replace("-", "_")


def get_model_profile(model_id: str) -> ModelProfile:
    """Return a supported benchmark profile and fail on silent substitutions."""
    try:
        return MODEL_PROFILES[model_id]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported benchmark model {model_id!r}. Use one of: {', '.join(MODEL_PROFILES)}"
        ) from exc
