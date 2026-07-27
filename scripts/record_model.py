#!/usr/bin/env python3
"""Resumable one-scenario cassette recording with per-model and whole-run guards."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = ROOT / "tests/llm/scenarios"
CASSETTE_ROOT = Path(
    os.environ.get(
        "VCR_CASSETTES_ROOT",
        str(ROOT / "tests/llm/vcr/cassettes"),
    )
)
PAID_RUN_CONFIRMATION = "RUN_PAID_BENCHMARK"
sys.path.insert(0, str(ROOT))

from scripts.local_env import load_local_env  # noqa: E402
from tests.llm.models import get_model_profile, model_slug  # noqa: E402
from tests.llm.vcr.cassette import CassetteManifest  # noqa: E402


def slug(model: str) -> str:
    return model_slug(model)


def run(command: list[str], env: dict[str, str]) -> int:
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


def _finite_nonnegative(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a finite non-negative number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return number


def _finite_positive(name: str, value: object) -> float:
    number = _finite_nonnegative(name, value)
    if number <= 0:
        raise ValueError(f"{name} must be a finite number greater than zero")
    return number


def _require_paid_confirmation(parser: argparse.ArgumentParser) -> None:
    confirmation = os.environ.get("LLM_PAID_RUN_CONFIRMATION")
    if confirmation != PAID_RUN_CONFIRMATION:
        parser.error(
            "paid recording requires an explicit process-level acknowledgement: "
            f"LLM_PAID_RUN_CONFIRMATION={PAID_RUN_CONFIRMATION}"
        )


def _manifest_cost(manifest: Path, model: str) -> float:
    loaded = CassetteManifest.load(manifest, model)
    return sum(entry.cost for entry in loaded.entries.values())


def recorded_cost(model_dir: Path, model: str) -> float:
    """Return the accepted cost represented by one model manifest."""
    return _manifest_cost(model_dir / "_manifest.yaml", model)


def _cost_from_mapping(value: object, *, source: Path) -> float:
    try:
        return _finite_nonnegative(f"cost in {source}", value)
    except ValueError as exc:
        raise ValueError(f"invalid paid-cost metadata: {exc}") from exc


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
                payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                raise ValueError(f"cannot read accepted cost from {path}: {exc}") from exc
            if not isinstance(payload, dict) or not isinstance(payload.get("meta"), dict):
                raise ValueError(f"accepted cassette {path} has no meta mapping")
            total += _cost_from_mapping(payload["meta"].get("cost"), source=path)
            total = _finite_nonnegative("accepted session cost", total)
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
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read rejected cost from {path}: {exc}") from exc
        metadata = payload.get("metadata") if isinstance(payload, dict) else None
        if not isinstance(metadata, dict):
            raise ValueError(f"rejected response {path} has no metadata mapping")
        total += _cost_from_mapping(metadata.get("cost"), source=path)
        total = _finite_nonnegative("rejected session cost", total)
    return total


def paid_cost_since(
    cassette_root: Path,
    rejected_root: Path,
    *,
    since: float,
    model: str | None = None,
) -> float:
    """Return accepted plus rejected billed cost for this session."""
    accepted = accepted_cost_since(cassette_root, since=since, model=model)
    rejected = rejected_cost_since(rejected_root, since=since, model=model)
    return _finite_nonnegative("whole session cost", accepted + rejected)


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
) -> float:
    if explicit is not None:
        value = explicit
    elif environment_name in os.environ:
        try:
            value = float(os.environ[environment_name])
        except ValueError as exc:
            parser.error(f"{environment_name} must be a number: {exc}")
    else:
        parser.error(
            f"{environment_name} is required; set it in the process environment, "
            ".env, or the matching CLI option"
        )
    try:
        return _finite_positive(f"{environment_name} / CLI limit", value)
    except ValueError as exc:
        parser.error(str(exc))


def _budget_blocked(label: str, current: float, limit: float) -> bool:
    if current < limit:
        return False
    print(
        f"COST GUARD: {label} has paid ${current:.6f}; limit is ${limit:.6f}",
        file=sys.stderr,
    )
    return True


def _budget_exceeded(label: str, current: float, limit: float) -> bool:
    if current <= limit:
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
        help="Required positive per-model paid-cost guard; accepted and rejected responses count.",
    )
    parser.add_argument(
        "--max-total-cost-usd",
        type=float,
        default=None,
        help="Required positive whole-session paid-cost guard across all models.",
    )
    args = parser.parse_args()
    load_local_env()
    get_model_profile(args.model)

    per_model_limit = _resolve_limit(
        parser,
        explicit=args.max_cost_per_model_usd,
        environment_name="LLM_MAX_COST_PER_MODEL_USD",
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
        raw_session_started_at = float(env.get("LLM_RECORDING_STARTED_AT", started_at))
        session_started_at = _finite_nonnegative(
            "LLM_RECORDING_STARTED_AT",
            raw_session_started_at,
        )
    except ValueError as exc:
        parser.error(f"LLM_RECORDING_STARTED_AT must be a finite epoch number: {exc}")
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

        # Existing cassettes may be validated offline without acknowledgement.
        # Require a fresh process-level decision immediately before any missing
        # cassette can lead to a paid provider request.
        _require_paid_confirmation(parser)
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

    accepted_total = recorded_cost(model_dir, args.model)
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
