#!/usr/bin/env bash
set -euo pipefail

vcr_cassettes_root="$(python - <<'PY_CASSETTES'
from scripts.vcr_paths import resolve_cassette_root
print(resolve_cassette_root())
PY_CASSETTES
)"
export VCR_CASSETTES_ROOT="$vcr_cassettes_root"
unset OPENROUTER_API_KEY || true

mapfile -t models < <(python - <<'PY_MODELS'
from tests.llm.models import BENCHMARK_MODELS
print("\n".join(BENCHMARK_MODELS))
PY_MODELS
)

for model in "${models[@]}"; do
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  LLM_PROVIDER=openrouter \
  LLM_MODEL="$model" \
  VCR_MODE=playback \
  python -m pytest tests/llm/test_scenarios.py --run-llm --vcr-mode=playback -q
  python scripts/vcr_precommit.py --model "$model"
done
python scripts/check_cassette_policy.py
