from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from .client import LLMClient
from .evaluator import Evaluator
from .oracle import validate_scenario
from .runner import LLMTestRunner
from .vcr.config import VCRConfig

SCENARIO_DIR = Path(__file__).parent / "scenarios"


def discover_scenarios() -> list[pytest.ParameterSet]:
    requested = os.environ.get("IPBOX_SCENARIO")
    paths = sorted(SCENARIO_DIR.glob("*.yaml"))
    if requested:
        paths = [path for path in paths if path.stem == requested]
        if not paths:
            raise RuntimeError(
                f"IPBOX_SCENARIO matched no scenarios exactly; no exact scenario: {requested}"
            )
    return [pytest.param(path, id=path.stem) for path in paths]


@pytest.fixture(scope="session")
def llm_client() -> LLMClient | None:
    config = VCRConfig()
    if config.is_playback:
        return None
    return LLMClient(require_api_key=True)


@pytest.mark.llm
@pytest.mark.parametrize("scenario_path", discover_scenarios())
def test_ipbox_scenario(llm_client: LLMClient | None, scenario_path: Path) -> None:
    scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    validate_scenario(scenario)
    result = LLMTestRunner(llm_client).run_scenario(scenario_path)
    failures, warnings = Evaluator(scenario).evaluate(result["parsed_data"])
    for warning in warnings:
        print(f"[WARN] {warning}")
    if failures:
        messages = "\n".join(f"- {failure['type']}: {failure['message']}" for failure in failures)
        pytest.fail(f"Scenario {scenario_path.stem} failed:\n{messages}")
