#!/usr/bin/env python3
"""Validate cassette completeness and exact request identity."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.llm.models import BENCHMARK_MODELS  # noqa: E402
from tests.llm.oracle import validate_scenario  # noqa: E402
from tests.llm.runner import LLMTestRunner  # noqa: E402
from tests.llm.vcr.cassette import (
    Cassette,
    CassetteManifest,
    parsed_response_equal_ignoring_meta_timestamp,
)  # noqa: E402
from tests.llm.vcr.config import VCRConfig  # noqa: E402
from tests.llm.vcr.fingerprint import compute_fingerprint  # noqa: E402


def orphan_cassette_ids(model_directory: Path, expected_ids: set[str]) -> set[str]:
    return {
        path.stem for path in model_directory.glob("*.yaml") if path.name != "_manifest.yaml"
    } - expected_ids


def cassette_payload_errors(
    cassette: Cassette,
    reparsed: dict[str, Any],
    expected_model: str | None = None,
) -> list[str]:
    """Return payload-integrity errors shared by pre-commit and unit tests."""
    errors: list[str] = []
    if cassette.meta.finish_reason != "stop":
        errors.append(f"finish_reason must be 'stop', got {cassette.meta.finish_reason!r}")
    if expected_model is not None and cassette.meta.returned_model != expected_model:
        errors.append(
            f"returned_model must equal requested model {expected_model!r}, "
            f"got {cassette.meta.returned_model!r}"
        )
    if not parsed_response_equal_ignoring_meta_timestamp(reparsed, cassette.parsed_response):
        errors.append("stored parsed_response differs from reparsed response")
    return errors


def validate_model(model: str) -> list[str]:
    os.environ.update(
        {
            "LLM_PROVIDER": "openrouter",
            "LLM_MODEL": model,
            "VCR_MODE": "playback",
            "VCR_CASSETTES_ROOT": str(ROOT / "tests/llm/vcr/cassettes"),
        }
    )
    config = VCRConfig()
    runner = LLMTestRunner(None)
    errors: list[str] = []
    paths = sorted((ROOT / "tests/llm/scenarios").glob("*.yaml"))
    try:
        manifest = CassetteManifest.load(config.manifest_path, model)
    except Exception as exc:
        return [f"{model}: invalid/missing manifest: {exc}"]

    expected_ids: set[str] = set()
    algorithm = (ROOT / "ipbox_algorytm.md").read_text(encoding="utf-8")
    for path in paths:
        scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
        validate_scenario(scenario)
        scenario_id = str(scenario["meta"]["id"])
        expected_ids.add(scenario_id)
        cassette_path = config.cassette_path(scenario_id)
        if not cassette_path.exists():
            errors.append(f"{model}: missing {scenario_id}")
            continue
        try:
            cassette = Cassette.load(cassette_path)
            prompt = runner.build_prompt(algorithm, scenario)
            request = runner.request_spec(prompt, config)
            request_hash = request.request_hash()
            fingerprint = compute_fingerprint(path, request_hash)
            if cassette.meta.requested_model != model:
                errors.append(f"{model}/{scenario_id}: requested model mismatch")
            if cassette.meta.request_hash != request_hash:
                errors.append(f"{model}/{scenario_id}: request hash mismatch")
            if cassette.meta.fingerprint != fingerprint:
                errors.append(f"{model}/{scenario_id}: fingerprint mismatch")
            reparsed = runner.validate_semantics(cassette.response, scenario)
            errors.extend(
                f"{model}/{scenario_id}: {error}"
                for error in cassette_payload_errors(cassette, reparsed, model)
            )
            entry = manifest.entries.get(scenario_id)
            if not isinstance(entry, dict):
                errors.append(f"{model}/{scenario_id}: manifest entry missing")
            else:
                if entry.get("file") != cassette_path.name:
                    errors.append(f"{model}/{scenario_id}: manifest filename mismatch")
                if entry.get("request_hash") != request_hash:
                    errors.append(f"{model}/{scenario_id}: manifest request hash mismatch")
                if entry.get("fingerprint") != fingerprint:
                    errors.append(f"{model}/{scenario_id}: manifest fingerprint mismatch")
                if entry.get("returned_model") != cassette.meta.returned_model:
                    errors.append(f"{model}/{scenario_id}: manifest returned_model mismatch")
                if entry.get("recorded_at") != cassette.meta.recorded_at:
                    errors.append(f"{model}/{scenario_id}: manifest recorded_at mismatch")
                if entry.get("cost") != cassette.meta.cost:
                    errors.append(f"{model}/{scenario_id}: manifest cost mismatch")
        except Exception as exc:
            errors.append(f"{model}/{scenario_id}: {exc}")

    cassette_ids = {
        path.stem for path in config.model_directory.glob("*.yaml") if path.name != "_manifest.yaml"
    }
    for orphan in sorted(cassette_ids - expected_ids):
        errors.append(f"{model}: orphan cassette file {orphan}")
    for orphan in sorted(set(manifest.entries) - expected_ids):
        errors.append(f"{model}: orphan manifest entry {orphan}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--model")
    group.add_argument("--all-models", action="store_true")
    args = parser.parse_args()
    models = BENCHMARK_MODELS if args.all_models else (args.model,)
    errors = [error for model in models for error in validate_model(model)]
    if errors:
        print("VCR validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    scenario_count = len(list((ROOT / "tests/llm/scenarios").glob("*.yaml")))
    print(f"VCR validation passed for {len(models)} model(s), {scenario_count} scenarios each")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
