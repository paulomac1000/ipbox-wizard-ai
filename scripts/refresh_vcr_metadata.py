#!/usr/bin/env python3
"""Refresh cassette-derived metadata from existing raw responses without API calls."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_helper.report_metadata import engine_source_hash  # noqa: E402
from tests.llm.models import BENCHMARK_MODELS  # noqa: E402
from tests.llm.oracle import validate_scenario  # noqa: E402
from tests.llm.runner import LLMTestRunner  # noqa: E402
from tests.llm.vcr.cassette import Cassette, CassetteManifest  # noqa: E402
from tests.llm.vcr.config import VCRConfig  # noqa: E402
from tests.llm.vcr.fingerprint import compute_fingerprint  # noqa: E402

CASSETTE_ROOT = ROOT / "tests/llm/vcr/cassettes"
SCENARIO_ROOT = ROOT / "tests/llm/scenarios"


def refresh_model(model: str, *, write: bool) -> int:
    os.environ.update(
        {
            "LLM_PROVIDER": "openrouter",
            "LLM_MODEL": model,
            "VCR_MODE": "playback",
            "VCR_CASSETTES_ROOT": str(CASSETTE_ROOT),
            "IPBOX_CODE_REVISION": f"engine:{engine_source_hash(ROOT)}",
        }
    )
    config = VCRConfig()
    runner = LLMTestRunner(None)
    manifest = CassetteManifest(model=model)
    algorithm = (ROOT / "ipbox_algorytm.md").read_text(encoding="utf-8")
    expected_ids: set[str] = set()
    changed = 0

    for scenario_path in sorted(SCENARIO_ROOT.glob("*.yaml")):
        scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
        validate_scenario(scenario)
        scenario_id = str(scenario["meta"]["id"])
        expected_ids.add(scenario_id)
        cassette_path = config.cassette_path(scenario_id)
        if not cassette_path.exists():
            raise FileNotFoundError(f"{model}: missing cassette {scenario_id}")
        cassette = Cassette.load(cassette_path)
        if cassette.meta.requested_model != model or cassette.meta.returned_model != model:
            raise ValueError(f"{model}/{scenario_id}: model identity mismatch")

        previous_meta = cassette.parsed_response.get("calculation_meta") or {}
        calculated_at = previous_meta.get("calculated_at") or cassette.meta.recorded_at
        os.environ["IPBOX_CALCULATED_AT"] = str(calculated_at)
        prompt = runner.build_prompt(algorithm, scenario)
        request = runner.request_spec(prompt, config)
        request_hash = request.request_hash()
        parsed = runner.validate_semantics(cassette.response, scenario)
        refreshed = Cassette(
            meta=replace(
                cassette.meta,
                request_hash=request_hash,
                fingerprint=compute_fingerprint(scenario_path, request_hash),
            ),
            response=cassette.response,
            parsed_response=parsed,
        )
        manifest.update(refreshed, cassette_path.name)
        if refreshed.to_yaml() != cassette.to_yaml():
            changed += 1
        if write:
            refreshed.save(cassette_path)

    actual_ids = {
        path.stem for path in config.model_directory.glob("*.yaml") if path.name != "_manifest.yaml"
    }
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        raise ValueError(f"{model}: cassette set mismatch; missing={missing}, extra={extra}")
    if write:
        manifest.save(config.manifest_path)
    print(f"{model}: validated={len(expected_ids)}, refreshed={changed}, write={write}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--model")
    group.add_argument("--all-models", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    models = BENCHMARK_MODELS if args.all_models else (args.model,)
    total = sum(refresh_model(model, write=args.write) for model in models)
    print(f"Total cassette payloads requiring refresh: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
