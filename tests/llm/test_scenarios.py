import glob
import os
from pathlib import Path

import pytest
import yaml

from .client import LLMClient
from .evaluator import Evaluator
from .runner import LLMTestRunner

_SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def _scenario_id(path: str) -> str:
    return Path(path).stem


def discover_scenarios() -> list:
    files = sorted(glob.glob(str(_SCENARIOS_DIR / "*.yaml")))
    limit = int(os.getenv("LLM_MAX_CALLS_PER_RUN", "0"))
    if limit > 0:
        files = files[:limit]

    params = []
    for f in files:
        path = Path(f)
        marks = []
        # Mark basic scenarios as smoke
        if path.name.startswith("01_") or path.name.startswith("02_"):
            marks.append(pytest.mark.smoke)

        params.append(pytest.param(f, marks=marks, id=path.stem))

    return params


@pytest.fixture(scope="session")
def llm_client(request):
    is_vs_code = request.config.pluginmanager.has_plugin("vscode_pytest") or os.getenv("TERM_PROGRAM") == "vscode"

    if not request.config.getoption("--run-llm") and not is_vs_code:
        pytest.skip("Skipped LLM tests — run with flag --run-llm")

    vcr_mode = request.config.getoption("--vcr-mode") or os.getenv("VCR_MODE") or "auto"

    # Reset VCR singleton between mode changes
    from .runner import _reset_vcr
    _reset_vcr()

    # In playback mode we don't need the real API key
    if vcr_mode == "playback":
        return LLMClient(require_api_key=False)

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.fail("OPENROUTER_API_KEY not set — required for LLM tests in non-playback mode")
    return LLMClient()


@pytest.mark.llm
@pytest.mark.parametrize("scenario_path", discover_scenarios())
def test_ipbox_scenario(llm_client, scenario_path):
    with open(scenario_path, encoding="utf-8") as f:
        scenario = yaml.safe_load(f)

    meta = scenario.get("meta", {})

    if meta.get("skip"):
        pytest.skip(f"Scenario marked as skipped: {meta.get('skip_reason', 'WIP')}")

    runner = LLMTestRunner(llm_client)
    result = runner.run_scenario(scenario_path)

    evaluator = Evaluator(scenario)
    failures, warnings = evaluator.evaluate(result["parsed_data"])

    for w in warnings:
        print(f"[WARN] {w}")

    if failures:
        msgs = "\n".join(f"  - {f['type']}: {f['message']}" for f in failures)
        pytest.fail(f"Scenario '{meta.get('id', scenario_path)}' failed:\n{msgs}")
