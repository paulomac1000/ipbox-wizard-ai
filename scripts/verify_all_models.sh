#!/usr/bin/env bash
set -euo pipefail
unset OPENROUTER_API_KEY || true

models=(
  "google/gemini-3.5-flash"
  "openai/gpt-5-mini"
  "anthropic/claude-haiku-4.5"
)

for model in "${models[@]}"; do
  LLM_PROVIDER=openrouter \
  LLM_MODEL="$model" \
  VCR_MODE=playback \
  pytest tests/llm/test_scenarios.py --run-llm --vcr-mode=playback -q
  python scripts/vcr_precommit.py --model "$model"
done
python scripts/check_cassette_policy.py
