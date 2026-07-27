#!/usr/bin/env bash
set -euo pipefail

EXPECTED_CONFIRMATION='RUN_PAID_BENCHMARK'
if [[ "${LLM_PAID_RUN_CONFIRMATION:-}" != "$EXPECTED_CONFIRMATION" ]]; then
  echo "Refusing paid recording: set LLM_PAID_RUN_CONFIRMATION=$EXPECTED_CONFIRMATION explicitly in the process environment" >&2
  exit 2
fi

ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q
for script in scripts/*.sh; do bash -n "$script"; done

export LLM_RECORDING_STARTED_AT="${LLM_RECORDING_STARTED_AT:-$(python - <<'PY_TIME'
import time
print(time.time())
PY_TIME
)}"
if [[ ! -v VCR_REJECTED_ROOT ]]; then
  export VCR_REJECTED_ROOT="$(
    python scripts/local_env.py \
      --get VCR_REJECTED_ROOT \
      --default /tmp/ipbox_llm_rejected
  )"
fi
if [[ -z "$VCR_REJECTED_ROOT" ]]; then
  echo 'VCR_REJECTED_ROOT must not be empty' >&2
  exit 2
fi
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
