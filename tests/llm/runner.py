import os
import re
import yaml
from pathlib import Path
from typing import Any

from .client import LLMClient

_RESPONSE_DIR = Path("/tmp/ipbox_llm_responses")

TAGS = ["result", "classifications", "monthly_W", "tests", "stops_reviews"]

# VCR integration (lazy import to avoid circular deps)
_vcr_recorder = None
_vcr_config = None


def _get_vcr_recorder():
    """Get or create VCR recorder singleton."""
    global _vcr_recorder, _vcr_config
    if _vcr_recorder is None:
        from .vcr import VCRRecorder, VCRConfig
        _vcr_config = VCRConfig()
        _vcr_recorder = VCRRecorder(_vcr_config)
    return _vcr_recorder


def _get_vcr_config():
    """Get VCR config singleton."""
    global _vcr_config
    if _vcr_config is None:
        from .vcr import VCRConfig
        _vcr_config = VCRConfig()
    return _vcr_config


class LLMTestRunner:
    """Batch mode — LLM executes phases 0-10 in one pass."""

    def __init__(self, client: LLMClient, algorithm_path: str = "ipbox_algorytm.md"):
        self.client = client
        self.algorithm_path = algorithm_path

    def build_prompt(self, algorithm: str, scenario: dict) -> str:
        input_yaml = yaml.dump(scenario.get("input", {}), allow_unicode=True)
        return f"""Jesteś agentem AI wykonującym algorytm IP Box w trybie BATCH.

ALGORYTM:
{algorithm}

DANE WEJŚCIOWE:
{input_yaml}

WYMAGANY FORMAT ODPOWIEDZI:
Wykonaj wszystkie fazy algorytmu (0-10) i zwróć wyniki w poniższych tagach.

<result>
# Pełny YAML z Fazy 10.2 - raport roczny z kluczami po polsku
</result>

<classifications>
# Lista pozycji KPiR: opis -> koszyk (IP / MIX / NIE / WYKLUCZONE)
</classifications>

<monthly_W>
# Tabela: miesiąc -> współczynnik W (np. 2025-01: 90.48)
</monthly_W>

<tests>
# Wyniki testów weryfikacyjnych: TEST_1: PASS/FAIL, TEST_2: PASS/FAIL, itd.
</tests>

<stops_reviews>
stops: []
reviews: []
</stops_reviews>
"""

    def run_scenario(self, scenario_path: str) -> dict:
        with open(scenario_path, encoding="utf-8") as f:
            scenario = yaml.safe_load(f)

        with open(self.algorithm_path, encoding="utf-8") as f:
            algorithm = f.read()

        prompt = self.build_prompt(algorithm, scenario)
        
        # Get VCR recorder and check if we should use it
        scenario_id = scenario["meta"]["id"]
        scenario_name = scenario["meta"].get("name", scenario_id)
        
        # Try VCR first (if not in none mode)
        config = _get_vcr_config()
        if not config.is_none:
            try:
                recorder = _get_vcr_recorder()
                response = recorder.get_or_record(
                    scenario_id=scenario_id,
                    scenario_path=Path(scenario_path),
                    prompt=prompt,
                    api_call_fn=lambda p: self.client.call_with_retry(
                        system_prompt="Jesteś ekspertem podatkowym specjalizującym się w IP Box (art. 30ca PIT). Wykonujesz obliczenia dokładnie i strukturalnie.",
                        user_prompt=p,
                    ),
                    scenario_name=scenario_name,
                )
            except Exception as e:
                # VCR failed (e.g., cassette issues) — fall back to direct API
                print(f"  ⚠️  VCR failed for {scenario_id}: {e}. Using live API.")
                response = self.client.call_with_retry(
                    system_prompt="Jesteś ekspertem podatkowym specjalizującym się w IP Box (art. 30ca PIT). Wykonujesz obliczenia dokładnie i strukturalnie.",
                    user_prompt=prompt,
                )
        else:
            # VCR disabled — always use live API
            response = self.client.call_with_retry(
                system_prompt="Jesteś ekspertem podatkowym specjalizującym się w IP Box (art. 30ca PIT). Wykonujesz obliczenia dokładnie i strukturalnie.",
                user_prompt=prompt,
            )

        self._save_response(scenario["meta"]["id"], response)

        return {
            "scenario_id": scenario["meta"]["id"],
            "raw_response": response,
            "parsed_data": self._extract_tags(response),
        }

    def _extract_tags(self, text: str) -> dict[str, Any]:
        extracted: dict[str, Any] = {}
        for tag in TAGS:
            match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
            if not match:
                extracted[tag] = None
                continue
            content = match.group(1).strip()
            if tag in ("result", "stops_reviews"):
                clean = _strip_code_block(content)
                try:
                    extracted[tag] = yaml.safe_load(clean)
                except yaml.YAMLError:
                    extracted[tag] = content
            else:
                extracted[tag] = content
        return extracted

    def _save_response(self, scenario_id: str, response: str) -> None:
        try:
            _RESPONSE_DIR.mkdir(parents=True, exist_ok=True)
            path = _RESPONSE_DIR / f"{scenario_id}.txt"
            path.write_text(response, encoding="utf-8")
        except OSError:
            pass


def _strip_code_block(text: str) -> str:
    m = re.search(r"```(?:yaml)?\n(.*?)\n```", text, re.DOTALL)
    return m.group(1) if m else text
