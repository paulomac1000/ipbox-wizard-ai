"""Candidate model profiles kept outside the released cassette engine hash."""

from __future__ import annotations

from .models import MODEL_PROFILES, ModelProfile

OPENAI_MODEL = "openai/gpt-5-mini"

CANDIDATE_MODEL_PROFILES: dict[str, ModelProfile] = {
    OPENAI_MODEL: ModelProfile(
        model_id=OPENAI_MODEL,
        label="OpenAI GPT-5 Mini",
        family="OpenAI GPT",
        reasoning={"effort": "minimal"},
    ),
}
CANDIDATE_MODELS = tuple(CANDIDATE_MODEL_PROFILES)


def register_candidate_models() -> None:
    """Register candidates explicitly without changing the released model matrix."""
    for model_id, profile in CANDIDATE_MODEL_PROFILES.items():
        existing = MODEL_PROFILES.get(model_id)
        if existing is not None and existing != profile:
            raise RuntimeError(f"Conflicting model profile for {model_id}")
        MODEL_PROFILES[model_id] = profile
