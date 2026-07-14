#!/usr/bin/env python3
"""Resumable, one-scenario-at-a-time cassette recording with a soft cost guard."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = ROOT / "tests/llm/scenarios"
CASSETTE_ROOT = ROOT / "tests/llm/vcr/cassettes"
sys.path.insert(0, str(ROOT))

from tests.llm.models import get_model_profile  # noqa: E402


def slug(model: str) -> str:
    return model.replace("/", "_").replace(".", "_").replace("-", "_")


def run(command: list[str], env: dict[str, str]) -> int:
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


def recorded_cost(model_dir: Path) -> float:
    manifest = model_dir / "_manifest.yaml"
    if not manifest.exists():
        return 0.0
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    entries = data.get("entries") or {}
    if not isinstance(entries, dict):
        return 0.0
    return sum(
        float(entry.get("cost") or 0) for entry in entries.values() if isinstance(entry, dict)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--scenario")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--max-cost-usd",
        type=float,
        default=float(os.environ.get("LLM_MAX_COST_USD", "0")),
        help="Soft per-model guard; 0 disables it. Checked before each new request.",
    )
    args = parser.parse_args()
    get_model_profile(args.model)

    if args.max_cost_usd < 0:
        parser.error("--max-cost-usd must be >= 0")
    if not os.environ.get("OPENROUTER_API_KEY"):
        parser.error("OPENROUTER_API_KEY is required")

    env = os.environ.copy()
    env.update(
        {
            "LLM_PROVIDER": "openrouter",
            "LLM_MODEL": args.model,
            "VCR_MODE": "record",
            "VCR_CASSETTES_ROOT": str(CASSETTE_ROOT),
        }
    )
    model_dir = CASSETTE_ROOT / slug(args.model)
    scenarios = sorted(SCENARIO_DIR.glob("*.yaml"))
    if args.scenario:
        scenarios = [
            path
            for path in scenarios
            if path.stem == args.scenario or path.stem.startswith(args.scenario)
        ]
        if not scenarios:
            parser.error(f"No scenario matches {args.scenario!r}")

    failures: list[str] = []
    skipped = 0
    for path in scenarios:
        cassette = model_dir / f"{path.stem}.yaml"
        env["IPBOX_SCENARIO"] = path.stem
        if cassette.exists() and not args.force:
            playback_env = env.copy()
            playback_env.pop("OPENROUTER_API_KEY", None)
            playback_env["VCR_MODE"] = "playback"
            playback_code = run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/llm/test_scenarios.py",
                    "--run-llm",
                    "--vcr-mode=playback",
                    "-q",
                    "--tb=short",
                ],
                playback_env,
            )
            if playback_code == 0:
                print(f"SKIP {path.stem}: existing cassette passed offline validation")
                skipped += 1
                continue
            print(f"STALE {path.stem}: preserving old file until a valid replacement is recorded")

        current_cost = recorded_cost(model_dir)
        if args.max_cost_usd and current_cost >= args.max_cost_usd:
            print(
                f"COST GUARD: {args.model} has recorded ${current_cost:.6f}; "
                f"limit is ${args.max_cost_usd:.6f}",
                file=sys.stderr,
            )
            failures.append(path.stem)
            failures.extend(
                item.stem for item in scenarios if not (model_dir / f"{item.stem}.yaml").exists()
            )
            break

        code = run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/llm/test_scenarios.py",
                "--run-llm",
                "--vcr-mode=record",
                "-q",
                "--tb=short",
            ],
            env,
        )
        if code:
            failures.append(path.stem)

    print(
        f"Model {args.model}: existing={skipped}, failed={len(set(failures))}, "
        f"recorded_cost=${recorded_cost(model_dir):.6f}, cassette_dir={model_dir}"
    )
    if failures:
        print("Failed scenarios:", ", ".join(sorted(set(failures))), file=sys.stderr)
        print("Inspect /tmp/ipbox_llm_rejected and rerun only missing scenarios.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
