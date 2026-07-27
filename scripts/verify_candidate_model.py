#!/usr/bin/env python3
"""Verify and report one candidate model without widening the release matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.llm.candidate_models import CANDIDATE_MODELS, register_candidate_models  # noqa: E402

register_candidate_models()

from scripts.benchmark_report import scenario_ids_from_yaml, summarize_model  # noqa: E402
from scripts.vcr_precommit import validate_model  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, choices=CANDIDATE_MODELS)
    parser.add_argument("--output", default="reports/benchmark-summary.json")
    args = parser.parse_args()

    errors = validate_model(args.model)
    scenario_ids = scenario_ids_from_yaml()
    row = summarize_model(args.model, scenario_ids)
    payload = {
        "scenario_count": len(scenario_ids),
        "models": [row],
        "all_complete_and_valid": not errors and bool(row["complete_and_valid"]),
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if errors:
        print("Candidate VCR validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Candidate VCR validation passed for {args.model}, {len(scenario_ids)} scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
