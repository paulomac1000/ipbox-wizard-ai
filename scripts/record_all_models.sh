#!/usr/bin/env bash
set -euo pipefail

python - <<'PY_ENV'
import os

from scripts.local_env import load_local_env

load_local_env()
if not os.environ.get("OPENROUTER_API_KEY"):
    raise SystemExit(
        "OPENROUTER_API_KEY is missing. Set it in the process environment or in an ignored .env file."
    )
PY_ENV

ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q
for script in scripts/*.sh dump-to-md.sh; do bash -n "$script"; done

export LLM_RECORDING_STARTED_AT="${LLM_RECORDING_STARTED_AT:-$(python - <<'PY_TIME'
import time
print(time.time())
PY_TIME
)}"
export VCR_REJECTED_ROOT="${VCR_REJECTED_ROOT:-/tmp/ipbox_llm_rejected}"
printf 'Recording session started at %s; rejected responses: %s\n' \
  "$LLM_RECORDING_STARTED_AT" "$VCR_REJECTED_ROOT"

mapfile -t models < <(python - <<'PY_MODELS'
from tests.llm.models import BENCHMARK_MODELS
print("\n".join(BENCHMARK_MODELS))
PY_MODELS
)

failed=()
for model in "${models[@]}"; do
  if ! python scripts/record_model.py --model "$model" "${@}"; then
    failed+=("$model")
    break
  fi
done

python scripts/benchmark_report.py || true
if ((${#failed[@]})); then
  printf 'Recording stopped after failure for: %s\n' "${failed[*]}" >&2
  exit 1
fi

./scripts/verify_all_models.sh
python scripts/benchmark_report.py
