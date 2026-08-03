from __future__ import annotations

import math
import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-llm", action="store_true", default=False)
    parser.addoption(
        "--vcr-mode",
        choices=("playback", "record", "none"),
        default=None,
    )
    parser.addoption("--llm-model", default=None)
    parser.addoption("--scenario", default=None)


def _require_paid_live_test_guards(mode: str) -> None:
    if mode not in {"record", "none"}:
        return
    if os.environ.get("LLM_PAID_RUN_CONFIRMATION") != "RUN_PAID_BENCHMARK":
        raise pytest.UsageError(
            "live LLM pytest modes require LLM_PAID_RUN_CONFIRMATION=RUN_PAID_BENCHMARK"
        )
    for name in ("LLM_MAX_COST_PER_MODEL_USD", "LLM_MAX_TOTAL_COST_USD"):
        raw = os.environ.get(name, "").strip()
        try:
            value = float(raw)
        except ValueError as exc:
            raise pytest.UsageError(f"{name} must be a finite positive number") from exc
        if not math.isfinite(value) or value <= 0:
            raise pytest.UsageError(f"{name} must be a finite positive number")


def pytest_configure(config: pytest.Config) -> None:
    mode = config.getoption("--vcr-mode") or os.environ.get("VCR_MODE", "playback")
    if config.getoption("--run-llm"):
        _require_paid_live_test_guards(mode)
    if configured_mode := config.getoption("--vcr-mode"):
        os.environ["VCR_MODE"] = configured_mode
    if model := config.getoption("--llm-model"):
        os.environ["LLM_MODEL"] = model
    if scenario := config.getoption("--scenario"):
        os.environ["IPBOX_SCENARIO"] = scenario


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-llm"):
        return
    marker = pytest.mark.skip(reason="LLM tests require --run-llm")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(marker)
