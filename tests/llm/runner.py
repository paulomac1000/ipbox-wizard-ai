"""Provider-neutral deterministic-first LLM scenario runner."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .client import LLMClient, LLMResponse
from .evaluator import Evaluator
from .oracle import (
    REVIEW_FACT_TO_CODE,
    STOP_FACT_TO_CODE,
    compute_reference,
)
from .output_schema import DECISION_JSON_SCHEMA, OUTPUT_JSON_SCHEMA
from .request_spec import LLMRequestSpec
from .vcr import VCRConfig, VCRRecorder

SYSTEM_PROMPT = (
    "Jesteś warstwą decyzyjną systemu IP Box. Otrzymujesz atomowe fakty ustalone "
    "przez deterministyczny kod. Nie wykonujesz arytmetyki, nie analizujesz ponownie "
    "danych podatkowych i nie tworzysz dodatkowych przesłanek. Zwracasz wyłącznie "
    "krótki obiekt JSON zgodny ze schematem decyzji."
)
RESPONSE_ROOT = Path("/tmp/ipbox_llm_responses")


def build_tool_context(reference: dict[str, Any]) -> dict[str, Any]:
    """Expose only authoritative atomic facts needed by the model decision layer."""
    return {"decision_facts": reference["decision_facts"]}


def build_decision_protocol() -> str:
    """Render the exact code-owned decision table used by the benchmark prompt."""
    lines = [
        "PROTOKÓŁ DECYZYJNY:",
        "- Dodaj kod wtedy i tylko wtedy, gdy przypisany mu fakt ma wartość true.",
        "- Nie dodawaj kodów dla faktów false i nie wyprowadzaj nowych faktów.",
        "- Kolejność kodów nie ma znaczenia, ale nie powtarzaj kodów.",
        "- status=STOPPED, gdy lista stops nie jest pusta; inaczej status=FINAL.",
        "",
        "STOP:",
    ]
    lines.extend(f"- {fact}=true -> {code}" for fact, code in STOP_FACT_TO_CODE.items())
    lines.append("")
    lines.append("REVIEW:")
    lines.extend(f"- {fact}=true -> {code}" for fact, code in REVIEW_FACT_TO_CODE.items())
    return "\n".join(lines)


def assemble_response(reference: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Merge the small model decision with the deterministic financial report."""
    return {
        "status": decision["status"],
        "result": deepcopy(reference["result"]),
        "classifications": deepcopy(reference["classifications"]),
        "monthly_W": deepcopy(reference["monthly_W"]),
        "tests": deepcopy(reference["tests"]),
        "stops_reviews": {
            "stops": sorted(decision["stops"]),
            "reviews": sorted(decision["reviews"]),
            "warnings": deepcopy(reference["stops_reviews"]["warnings"]),
        },
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
        self.decision_validator = Draft202012Validator(DECISION_JSON_SCHEMA["schema"])
        self.output_validator = Draft202012Validator(OUTPUT_JSON_SCHEMA["schema"])

    def build_prompt(self, algorithm: str, scenario: dict[str, Any]) -> str:
        del (
            algorithm
        )  # Human documentation is tested separately; request rules come from code maps.
        reference = compute_reference(scenario)
        payload = build_tool_context(reference)
        return (
            f"{build_decision_protocol()}\n\n"
            "AUTORYTATYWNE FAKTY:\n"
            f"{json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
            "Zwróć wyłącznie pola status, stops i reviews zgodnie ze schematem. "
            "Nie zwracaj raportu finansowego — system dołączy go deterministycznie.\n"
        )

    def request_spec(self, prompt: str, config: VCRConfig) -> LLMRequestSpec:
        profile = config.profile
        if profile.response_format_type == "json_object":
            response_format: dict[str, Any] = {"type": "json_object"}
            system_prompt = (
                SYSTEM_PROMPT
                + "\n\nOczekiwany strict JSON Schema:\n"
                + json.dumps(DECISION_JSON_SCHEMA["schema"], ensure_ascii=False, indent=2)
            )
        else:
            response_format = {"type": "json_schema", "json_schema": DECISION_JSON_SCHEMA}
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

    @staticmethod
    def _strip_markdown_fence(content: str) -> str:
        stripped = content.strip()
        if stripped.startswith("```"):
            for fence in ("```json\n", "```JSON\n", "```\n"):
                if stripped.startswith(fence):
                    stripped = stripped[len(fence) :]
                    break
            close_pos = stripped.rfind("\n```")
            if close_pos >= 0:
                stripped = stripped[:close_pos]
        return stripped.strip()

    def parse_decision(self, content: str) -> dict[str, Any]:
        try:
            parsed = json.loads(self._strip_markdown_fence(content))
        except json.JSONDecodeError as exc:
            raise ValueError("response must be pure JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("response root must be an object")
        errors = sorted(
            self.decision_validator.iter_errors(parsed),
            key=lambda item: list(item.path),
        )
        if errors:
            details = "; ".join(error.message for error in errors[:8])
            raise ValueError(f"decision does not match strict schema: {details}")
        for key in ("stops", "reviews"):
            codes = parsed[key]
            if len(codes) != len(set(codes)):
                raise ValueError(f"decision contains duplicate {key} codes")
        return parsed

    def validate_semantics(
        self,
        content: str,
        scenario: dict[str, Any],
    ) -> dict[str, Any]:
        decision = self.parse_decision(content)
        reference = compute_reference(scenario)
        parsed = assemble_response(reference, decision)
        schema_errors = sorted(
            self.output_validator.iter_errors(parsed),
            key=lambda item: list(item.path),
        )
        if schema_errors:
            details = "; ".join(error.message for error in schema_errors[:8])
            raise ValueError(f"assembled response does not match output schema: {details}")
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
