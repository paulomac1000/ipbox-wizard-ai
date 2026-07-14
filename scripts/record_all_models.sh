#!/usr/bin/env bash
set -uo pipefail

: "${OPENROUTER_API_KEY:?Set OPENROUTER_API_KEY before recording}"

ruff format --check . || exit 1
ruff check . || exit 1
python -m compileall -q python_helper tests scripts || exit 1
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90 || exit 1

models=(
  "google/gemini-3.5-flash"
  "openai/gpt-5-mini"
  "anthropic/claude-haiku-4.5"
)

failed=()
for model in "${models[@]}"; do
  if ! python scripts/record_model.py --model "$model" "${@}"; then
    failed+=("$model")
  fi
done

python scripts/benchmark_report.py || true
if ((${#failed[@]})); then
  printf 'Recording incomplete for: %s\n' "${failed[*]}" >&2
  exit 1
fi

./scripts/verify_all_models.sh
python scripts/benchmark_report.py
