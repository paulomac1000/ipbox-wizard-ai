from pathlib import Path

root = Path(__file__).resolve().parents[1]
(root / ".github/workflows/llm-scenario-tests.yml").write_text(
    '''name: LLM Scenario Record and Playback

on:
  workflow_dispatch:
    inputs:
      model:
        description: "OpenRouter model ID"
        required: true
        default: "google/gemini-3.5-flash"

permissions:
  contents: read

concurrency:
  group: llm-record-${{ github.ref }}
  cancel-in-progress: false

jobs:
  record:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    env:
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
      LLM_PROVIDER: openrouter
      LLM_MODEL: ${{ inputs.model }}
      VCR_MODE: record
      VCR_CASSETTES_ROOT: ${{ github.workspace }}/generated-cassettes

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-test.txt

      - name: Validate API key
        run: |
          set -euo pipefail
          test -n "$OPENROUTER_API_KEY" || {
            echo "::error::OPENROUTER_API_KEY is not configured"
            exit 1
          }

      - name: Validate deterministic suite before paid calls
        run: |
          set -euo pipefail
          ruff format --check .
          ruff check .
          python -m compileall -q python_helper tests
          pytest tests/unit \
            --cov=python_helper \
            --cov-report=term-missing \
            --cov-fail-under=90

      - name: Prepare empty cassette candidate directory
        run: |
          set -euo pipefail
          rm -rf "$VCR_CASSETTES_ROOT"
          mkdir -p "$VCR_CASSETTES_ROOT" reports

      - name: Record genuine responses
        run: |
          set -euo pipefail
          pytest tests/llm/test_scenarios.py \
            --run-llm \
            --vcr-mode=record \
            --junitxml=reports/llm-record.xml \
            -v --tb=long

      - name: Verify playback without API key
        run: |
          set -euo pipefail
          unset OPENROUTER_API_KEY
          export VCR_MODE=playback
          pytest tests/llm/test_scenarios.py \
            --run-llm \
            --vcr-mode=playback \
            --junitxml=reports/llm-playback.xml \
            -v --tb=long
          python scripts/vcr_precommit.py

      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: llm-reports-${{ github.run_id }}
          path: reports/
          if-no-files-found: warn
          retention-days: 14

      - name: Upload verified cassette candidate
        if: success()
        uses: actions/upload-artifact@v4
        with:
          name: llm-cassettes-${{ github.run_id }}
          path: generated-cassettes/
          if-no-files-found: error
          retention-days: 14
''',
    encoding="utf-8",
)
