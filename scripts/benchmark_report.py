#!/usr/bin/env python3
"""Produce a completeness, integrity and actual-cost report for cassette sets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.vcr_precommit import validate_model  # noqa: E402
from tests.llm.models import BENCHMARK_MODELS, get_model_profile, model_slug  # noqa: E402
from tests.llm.vcr.cassette import CassetteManifest  # noqa: E402


def slug(model: str) -> str:
    return model_slug(model)


def scenario_ids_from_yaml() -> set[str]:
    ids: set[str] = set()
    for path in sorted((ROOT / "tests/llm/scenarios").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        scenario_id = str((data.get("meta") or {}).get("id", ""))
        if not scenario_id:
            raise ValueError(f"{path}: missing meta.id")
        if scenario_id != path.stem:
            raise ValueError(f"{path}: meta.id={scenario_id!r} must equal filename stem")
        if scenario_id in ids:
            raise ValueError(f"duplicate scenario meta.id={scenario_id!r}")
        ids.add(scenario_id)
    return ids


def summarize_model(model: str, scenario_ids: set[str]) -> dict[str, object]:
    directory = ROOT / "tests/llm/vcr/cassettes" / slug(model)
    manifest_path = directory / "_manifest.yaml"
    manifest_errors: list[str] = []
    try:
        manifest = CassetteManifest.load(manifest_path, model)
        entries = manifest.entries
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        entries = {}
        manifest_errors.append(f"{model}: invalid/missing manifest: {exc}")

    cassette_ids = {path.stem for path in directory.glob("*.yaml") if path.name != "_manifest.yaml"}
    recorded = scenario_ids & set(entries) & cassette_ids
    cost = sum(entries[scenario_id].cost for scenario_id in recorded)
    errors = [*manifest_errors, *validate_model(model)]
    return {
        "model": model,
        "recorded": len(recorded),
        "missing": sorted(scenario_ids - recorded),
        "orphan_files": sorted(cassette_ids - scenario_ids),
        "orphan_manifest_entries": sorted(set(entries) - scenario_ids),
        "integrity_errors": errors,
        "actual_cost_usd": round(cost, 6),
        "complete_and_valid": not errors and recorded == scenario_ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--output", default="reports/benchmark-summary.json")
    args = parser.parse_args()

    models = tuple(args.models) if args.models else BENCHMARK_MODELS
    for model in models:
        get_model_profile(model)

    scenario_ids = scenario_ids_from_yaml()
    rows = [summarize_model(model, scenario_ids) for model in models]
    payload = {
        "scenario_count": len(scenario_ids),
        "models": rows,
        "all_complete_and_valid": all(row["complete_and_valid"] for row in rows),
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["all_complete_and_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
