import re
from pathlib import Path
from typing import Any

import yaml

from .client import LLMClient

_RESPONSE_DIR = Path("/tmp/ipbox_llm_responses")

SYSTEM_PROMPT = "Jesteś ekspertem podatkowym specjalizującym się w IP Box (art. 30ca PIT). Wykonujesz obliczenia dokładnie i strukturalnie."

TAGS = ["result", "classifications", "monthly_W", "tests", "stops_reviews"]

# VCR integration (lazy import to avoid circular deps)
_vcr_recorder = None
_vcr_config = None


def _reset_vcr():
    """Reset VCR singleton — use between mode switches (record ↔ playback)."""
    global _vcr_recorder, _vcr_config
    _vcr_recorder = None
    _vcr_config = None


def _get_vcr_recorder():
    """Get or create VCR recorder singleton."""
    global _vcr_recorder, _vcr_config
    if _vcr_recorder is None:
        from .vcr import VCRConfig, VCRRecorder
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
        import json as _json

        input_yaml = yaml.dump(scenario.get("input", {}), allow_unicode=True)
        json_example = _json.dumps(
            {
                "result": {
                    "rok": 2025,
                    "przychody_roczne": {"IP": 0.0, "NIE": 0.0},
                    "nexus": {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "poza_nexus": 0.0, "wartość": 0.0},
                    "podatek": {"podatek_IP": 0, "podatek_NIE_finalny": 0},
                },
                "classifications": [
                    {"opis": "example", "basket": "IP", "nexus_basket": "A", "nexus_amount": 0.0},
                ],
                "monthly_W": {"2025-01": 90.0},
                "tests": {"TEST_1": "PASS", "TEST_2": "FAIL"},
                "stops_reviews": {"stops": [], "reviews": [], "warnings": []},
            },
            indent=2,
            ensure_ascii=False,
        )
        return f"""Jesteś agentem AI wykonującym algorytm IP Box w trybie BATCH.

ALGORYTM:
{algorithm}

DANE WEJŚCIOWE:
{input_yaml}

WYMAGANY FORMAT ODPOWIEDZI:
Zwróć wyłącznie czysty JSON zgodny z poniższym schematem.
Bez żadnych tagów, znaczników XML, formatowania Markdown, bold, tabel, ani tekstu przed/po JSON.
Klucze po polsku, liczby jako liczby.

{json_example}
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
                    system_prompt=SYSTEM_PROMPT,
                    api_call_fn=lambda p: self.client.call_with_retry(
                        system_prompt=SYSTEM_PROMPT,
                        user_prompt=p,
                    ),
                    scenario_name=scenario_name,
                )
            except Exception as e:
                print(f"  ❌ VCR failed for {scenario_id}: {e}")
                raise
        else:
            # VCR disabled — always use live API
            response = self.client.call_with_retry(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
            )

        self._save_response(scenario["meta"]["id"], response)

        return {
            "scenario_id": scenario["meta"]["id"],
            "raw_response": response,
            "parsed_data": self._extract_tags(response),
        }

    def _extract_tags(self, text: str) -> dict[str, Any]:
        """Parse response — try JSON first (structured output), fallback to XML tags."""
        import json

        # Try strict JSON first
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "result" in data:
                return data
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: find first { and try progressively shorter suffixes
        start = text.find("{")
        if start >= 0:
            end = text.rfind("}")
            while end > start:
                try:
                    data = json.loads(text[start : end + 1])
                    if isinstance(data, dict) and "result" in data:
                        return data
                except (json.JSONDecodeError, ValueError):
                    pass
                end = text.rfind("}", 0, end)

        # Fallback: original regex tag extraction
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
