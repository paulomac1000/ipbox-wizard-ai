#!/usr/bin/env python3
"""Resumable one-scenario cassette recording with per-model and whole-run guards."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = ROOT / "tests/llm/scenarios"
CASSETTE_ROOT = ROOT / "tests/llm/vcr/cassettes"
sys.path.insert(0, str(ROOT))

from tests.llm.models import get_model_profile, model_slug  # noqa: E402


def slug(model: str) -> str:
    return model_slug(model)


def run(command: list[str], env: dict[str, str]) -> int:
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


def _manifest_cost(manifest: Path) -> float:
    if not manifest.exists():
        return 0.0
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    entries = data.get("entries") or {}
    if not isinstance(entries, dict):
        return 0.0
    return sum(
        float(entry.get("cost") or 0) for entry in entries.values() if isinstance(entry, dict)
    )


def recorded_cost(model_dir: Path) -> float:
    """Return the accepted cost represented by one model manifest."""
    return _manifest_cost(model_dir / "_manifest.yaml")


def accepted_cost_since(cassette_root: Path, *, since: float, model: str | None = None) -> float:
    """Count accepted paid calls written during the current recording session."""
    roots = [cassette_root / model] if model else list(cassette_root.glob("*"))
    total = 0.0
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.glob("*.yaml"):
            if path.name == "_manifest.yaml" or path.stat().st_mtime < since:
                continue
            try:
                payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                total += float((payload.get("meta") or {}).get("cost") or 0)
            except (OSError, TypeError, ValueError, yaml.YAMLError):
                continue
    return total


def rejected_cost_since(rejected_root: Path, *, since: float, model: str | None = None) -> float:
    """Count rejected but billed calls written during the current recording session."""
    root = rejected_root / model if model else rejected_root
    total = 0.0
    if not root.exists():
        return total
    for path in root.rglob("*.json"):
        if path.stat().st_mtime < since:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            total += float((payload.get("metadata") or {}).get("cost") or 0)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return total


def paid_cost_since(
    cassette_root: Path,
    rejected_root: Path,
    *,
    since: float,
    model: str | None = None,
) -> float:
    """Return accepted plus rejected billed cost for this session."""
    return accepted_cost_since(cassette_root, since=since, model=model) + rejected_cost_since(
        rejected_root,
        since=since,
        model=model,
    )


def select_scenarios(paths: list[Path], requested: str | None) -> list[Path]:
    """Select one exact scenario or return the complete sorted list."""
    ordered = sorted(paths)
    if not requested:
        return ordered
    matches = [path for path in ordered if path.stem == requested]
    if not matches:
        raise ValueError(f"No exact scenario matches {requested!r}")
    return matches


def _resolve_limit(
    parser: argparse.ArgumentParser,
    *,
    explicit: float | None,
    environment_name: str,
    fallback: float | None = None,
) -> float:
    if explicit is not None:
        value = explicit
    elif environment_name in os.environ:
        try:
            value = float(os.environ[environment_name])
        except ValueError as exc:
            parser.error(f"{environment_name} must be a number: {exc}")
    elif fallback is not None:
        value = fallback
    else:
        value = 0.0
    if value < 0:
        parser.error(f"{environment_name} / CLI limit must be >= 0")
    return value


def _budget_blocked(label: str, current: float, limit: float) -> bool:
    if not limit or current < limit:
        return False
    print(
        f"COST GUARD: {label} has paid ${current:.6f}; limit is ${limit:.6f}",
        file=sys.stderr,
    )
    return True


def _budget_exceeded(label: str, current: float, limit: float) -> bool:
    if not limit or current <= limit:
        return False
    print(
        f"COST GUARD EXCEEDED: {label} paid ${current:.6f}; limit is ${limit:.6f}. "
        "Billing is reported only after a response, so the request that crossed the limit "
        "was stopped immediately after accounting and no further request will start.",
        file=sys.stderr,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--scenario")
    parser.add_argument(
        "--max-cost-per-model-usd",
        type=float,
        default=None,
        help="Per-model paid-cost guard; accepted and rejected responses both count.",
    )
    parser.add_argument(
        "--max-total-cost-usd",
        type=float,
        default=None,
        help="Whole-session paid-cost guard across all models; 0 disables it.",
    )
    parser.add_argument(
        "--max-cost-usd",
        type=float,
        default=None,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    get_model_profile(args.model)

    if args.max_cost_usd is not None and args.max_cost_per_model_usd is not None:
        parser.error("use --max-cost-per-model-usd instead of combining it with --max-cost-usd")
    legacy_limit = args.max_cost_usd
    if legacy_limit is None and "LLM_MAX_COST_USD" in os.environ:
        try:
            legacy_limit = float(os.environ["LLM_MAX_COST_USD"])
        except ValueError as exc:
            parser.error(f"LLM_MAX_COST_USD must be a number: {exc}")
    per_model_limit = _resolve_limit(
        parser,
        explicit=args.max_cost_per_model_usd,
        environment_name="LLM_MAX_COST_PER_MODEL_USD",
        fallback=legacy_limit,
    )
    total_limit = _resolve_limit(
        parser,
        explicit=args.max_total_cost_usd,
        environment_name="LLM_MAX_TOTAL_COST_USD",
    )
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
    model_slug = slug(args.model)
    model_dir = CASSETTE_ROOT / model_slug
    rejected_root = Path(env.get("VCR_REJECTED_ROOT", "/tmp/ipbox_llm_rejected"))
    started_at = time.time()
    try:
        session_started_at = float(env.get("LLM_RECORDING_STARTED_AT", started_at))
    except ValueError as exc:
        parser.error(f"LLM_RECORDING_STARTED_AT must be an epoch number: {exc}")
    if session_started_at > started_at + 1:
        parser.error("LLM_RECORDING_STARTED_AT cannot be in the future")

    try:
        scenarios = select_scenarios(list(SCENARIO_DIR.glob("*.yaml")), args.scenario)
    except ValueError as exc:
        parser.error(str(exc))

    failures: list[str] = []
    skipped = 0
    for path in scenarios:
        cassette = model_dir / f"{path.stem}.yaml"
        env["IPBOX_SCENARIO"] = path.stem
        if cassette.exists():
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
            print(
                f"STALE {path.stem}: delete the cassette explicitly before re-recording",
                file=sys.stderr,
            )
            failures.append(path.stem)
            break

        model_paid = paid_cost_since(
            CASSETTE_ROOT,
            rejected_root,
            since=session_started_at,
            model=model_slug,
        )
        total_paid = paid_cost_since(
            CASSETTE_ROOT,
            rejected_root,
            since=session_started_at,
        )
        if _budget_blocked(args.model, model_paid, per_model_limit) or _budget_blocked(
            "whole recording session", total_paid, total_limit
        ):
            failures.append(path.stem)
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

        model_paid = paid_cost_since(
            CASSETTE_ROOT,
            rejected_root,
            since=session_started_at,
            model=model_slug,
        )
        total_paid = paid_cost_since(
            CASSETTE_ROOT,
            rejected_root,
            since=session_started_at,
        )
        if (
            code
            or _budget_exceeded(args.model, model_paid, per_model_limit)
            or _budget_exceeded("whole recording session", total_paid, total_limit)
        ):
            failures.append(path.stem)
            break

    accepted_total = recorded_cost(model_dir)
    model_session_paid = paid_cost_since(
        CASSETTE_ROOT,
        rejected_root,
        since=session_started_at,
        model=model_slug,
    )
    global_session_paid = paid_cost_since(
        CASSETTE_ROOT,
        rejected_root,
        since=session_started_at,
    )
    print(
        f"Model {args.model}: existing={skipped}, failed={len(set(failures))}, "
        f"accepted_manifest_cost=${accepted_total:.6f}, "
        f"model_session_paid=${model_session_paid:.6f}, "
        f"global_session_paid=${global_session_paid:.6f}, cassette_dir={model_dir}"
    )
    if failures:
        print("Failed scenarios:", ", ".join(sorted(set(failures))), file=sys.stderr)
        print(
            "Inspect VCR_REJECTED_ROOT and rerun only the exact missing scenario.", file=sys.stderr
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
