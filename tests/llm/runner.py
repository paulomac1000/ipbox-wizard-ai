"""Provider-neutral deterministic-first LLM scenario runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .client import LLMClient, LLMResponse
from .evaluator import Evaluator
from .oracle import compute_reference
from .output_schema import OUTPUT_JSON_SCHEMA
from .request_spec import LLMRequestSpec
from .vcr import VCRConfig, VCRRecorder

SYSTEM_PROMPT = (
    "Jesteś warstwą raportującą systemu IP Box. Nie wykonujesz arytmetyki w pamięci: "
    "korzystasz z przekazanych wyników deterministycznego kalkulatora. Stosujesz reguły "
    "STOP/REVIEW/TEST z algorytmu i zwracasz wyłącznie jeden obiekt JSON zgodny ze schematem."
)
RESPONSE_ROOT = Path("/tmp/ipbox_llm_responses")


def build_tool_context(reference: dict[str, Any]) -> dict[str, Any]:
    """Expose calculator output while leaving policy decisions for the model."""
    result = reference["result"]
    return {
        "calculator_result": result,
        "cost_classifications": reference["classifications"],
        "monthly_W": reference["monthly_W"],
        "validation_facts": {
            test_id: status == "PASS" for test_id, status in reference["tests"].items()
        },
        "diagnostic_facts": reference.get("diagnostic_facts", {}),
    }


class LLMTestRunner:
    """Run one normalized scenario through an exact request and fail-closed VCR."""

    def __init__(
        self,
        client: LLMClient | None,
        algorithm_path: str | Path = "ipbox_algorytm.md",
    ) -> None:
        self.client = client
        self.algorithm_path = Path(algorithm_path)
        self.validator = Draft202012Validator(OUTPUT_JSON_SCHEMA["schema"])

    def build_prompt(self, algorithm: str, scenario: dict[str, Any]) -> str:
        reference = compute_reference(scenario)
        payload = {
            "scenario": scenario["input"],
            "deterministic_tool_output": build_tool_context(reference),
        }
        return (
            "Wykonaj przypadek w trybie BATCH.\n\n"
            "ALGORYTM OPERACYJNY:\n"
            f"{algorithm}\n\n"
            "DANE I WYNIK NARZĘDZIA PYTHON:\n"
            f"{json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
            "ZASADY ODPOWIEDZI:\n"
            "1. Skopiuj liczby i klasyfikacje wyłącznie z deterministic_tool_output; "
            "nie przeliczaj ich.\n"
            "2. Na podstawie danych, diagnostic_facts i algorytmu wyznacz status, "
            "kody STOP/REVIEW/WARNING oraz TEST_1..TEST_9.\n"
            "3. Dla każdego REVIEW sprawdź odpowiadający mu fakt w diagnostic_facts "
            "(patrz sekcja 11 algorytmu).\n"
            "4. Każdy kod STOP jest niezależny — dodaj tylko te, których warunek "
            "jest spełniony. Nie kaskaduj.\n"
            "5. Jeżeli jest STOP, status=STOPPED, a wyniki finansowe mają być zerowe "
            "zgodnie z tool output.\n"
            "6. Nie dodawaj komentarzy, markdownu ani pól spoza schematu. Zwróć tylko JSON.\n"
            "\n"
            "LISTA KONTROLNA REVIEW (sprawdź każdy warunek z diagnostic_facts):\n"
            "- clients_with_positive_revenue == 1 → dodaj REVIEW_09\n"
            "- w_max > 95 → dodaj REVIEW_01\n"
            "- w_min < 50 → dodaj REVIEW_02\n"
            "- max_w_jump_pp > 30 → dodaj REVIEW_08\n"
            "- has_multiple_projects == true → dodaj REVIEW_04\n"
            "- uses_kis_interpretation == true → dodaj REVIEW_16 + REVIEW_17\n"
            "\n"
            "LISTA KONTROLNA STOP:\n"
            "- STOP_01: forma opodatkowania nieobsługiwana przez IP Box\n"
            "- STOP_02: brak kwalifikowanego prawa IP\n"
            "- STOP_03: brak dochodu z kwalifikowanego IP\n"
            "- STOP_04: brak prac B+R\n"
            "- STOP_08: przychód IP bez ewidencji lub dowodów B+R\n"
            "- ZUS_DOUBLE_DIP: składki społeczne w KPiR i odliczenie PIT > 0\n"
            "- HEALTH_DOUBLE_DIP: składka zdrowotna w kosztach i odliczenie > 0\n"
            "STOP-y są niezależne — dodaj TYLKO te, których warunek spełniony.\n"
        )

    def request_spec(self, prompt: str, config: VCRConfig) -> LLMRequestSpec:
        profile = config.profile
        if profile.response_format_type == "json_object":
            response_format: dict[str, Any] = {"type": "json_object"}
            system_prompt = (
                SYSTEM_PROMPT
                + "\n\nOczekiwany strict JSON Schema (zwróć dokładnie tę strukturę):\n"
                + json.dumps(OUTPUT_JSON_SCHEMA["schema"], ensure_ascii=False, indent=2)
            )
        else:
            response_format = {"type": "json_schema", "json_schema": OUTPUT_JSON_SCHEMA}
            system_prompt = SYSTEM_PROMPT
        return LLMRequestSpec(
            provider=config.provider,
            model=config.model,
            system_prompt=system_prompt,
            user_prompt=prompt,
            temperature=profile.temperature,
            max_tokens=profile.max_tokens,
            response_format=response_format,
            provider_preferences=None,
            seed=None,
            reasoning=profile.reasoning,
        )

    def parse_response(self, content: str) -> dict[str, Any]:
        stripped = content.strip()
        if stripped.startswith("```"):
            for fence in ("```json\n", "```JSON\n", "```\n"):
                if stripped.startswith(fence):
                    stripped = stripped[len(fence) :]
                    break
            close_pos = stripped.rfind("\n```")
            if close_pos >= 0:
                stripped = stripped[:close_pos]
            stripped = stripped.strip()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError("response must be pure JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("response root must be an object")
        errors = sorted(self.validator.iter_errors(parsed), key=lambda item: list(item.path))
        if errors:
            details = "; ".join(error.message for error in errors[:8])
            raise ValueError(f"response does not match strict schema: {details}")
        return parsed

    def validate_semantics(
        self,
        content: str,
        scenario: dict[str, Any],
    ) -> dict[str, Any]:
        parsed = self.parse_response(content)
        failures, _warnings = Evaluator(scenario).evaluate(parsed)
        if failures:
            details = "; ".join(
                f"{failure['type']}: {failure['message']}" for failure in failures[:12]
            )
            raise ValueError(f"semantic evaluation failed: {details}")
        return parsed

    def run_scenario(self, scenario_path: str | Path) -> dict[str, Any]:
        path = Path(scenario_path)
        scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
        algorithm = self.algorithm_path.read_text(encoding="utf-8")
        prompt = self.build_prompt(algorithm, scenario)
        config = VCRConfig()
        request = self.request_spec(prompt, config)
        recorder = VCRRecorder(config)
        response, parsed = recorder.get_or_record(
            scenario=scenario,
            scenario_path=path,
            request=request,
            api_call=self._call_live if self.client is not None else None,
            validate_response=lambda content: self.validate_semantics(content, scenario),
        )
        self._save_response(config.model_slug, str(scenario["meta"]["id"]), response, parsed)
        return {
            "scenario_id": str(scenario["meta"]["id"]),
            "raw_response": response.content,
            "parsed_data": parsed,
            "response_metadata": response,
        }

    def _call_live(self, request: LLMRequestSpec) -> LLMResponse:
        if self.client is None:
            raise ValueError("live mode requires LLMClient")
        return self.client.call_with_retry(request.api_payload())

    @staticmethod
    def _save_response(
        model_slug: str,
        scenario_id: str,
        response: LLMResponse,
        parsed: dict[str, Any],
    ) -> None:
        directory = RESPONSE_ROOT / model_slug
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{scenario_id}.json").write_text(
            json.dumps(
                {
                    "response": parsed,
                    "metadata": {
                        "request_id": response.request_id,
                        "requested_model": response.requested_model,
                        "returned_model": response.returned_model,
                        "finish_reason": response.finish_reason,
                        "prompt_tokens": response.prompt_tokens,
                        "completion_tokens": response.completion_tokens,
                        "total_tokens": response.total_tokens,
                        "cost": response.cost,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
