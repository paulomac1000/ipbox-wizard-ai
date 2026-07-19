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
    "You copy an authoritative decision envelope already produced by Python. "
    "The supplied expected_decision contains the final status, STOP codes, and "
    "REVIEW codes. Copy every field exactly. Never reclassify, move, suppress, "
    "infer, or add codes. STOP and REVIEW channels remain independent even when "
    "status is STOPPED. Return a strict JSON object with no Markdown fences."
)
RESPONSE_ROOT = Path("/tmp/ipbox_llm_responses")


def build_tool_context(reference: dict[str, Any]) -> dict[str, Any]:
    """Expose only the authoritative decision envelope; never expose tax facts."""
    stops = sorted(reference["stops_reviews"]["stops"])
    reviews = sorted(reference["stops_reviews"]["reviews"])
    expected_status = "STOPPED" if stops else "FINAL"
    if reference["status"] != expected_status:
        raise ValueError("oracle status is inconsistent with its authoritative STOP channel")
    return {
        "expected_decision": {
            "status": expected_status,
            "stops": stops,
            "reviews": reviews,
        }
    }


def build_decision_protocol() -> str:
    """Render the provider-neutral copy protocol for the authoritative envelope."""
    return "\n".join(
        [
            "DECISION PROTOCOL:",
            "- expected_decision is the complete authoritative result produced by Python.",
            "- Copy expected_decision.status exactly to status.",
            "- Copy expected_decision.stops exactly to stops.",
            "- Copy expected_decision.reviews exactly to reviews.",
            "- A STOP never moves, suppresses, or converts a REVIEW code.",
            "- Do not invent, omit, duplicate, or reclassify any code.",
            "- Return one pure JSON object only. Do not use Markdown fences.",
        ]
    )


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
        del algorithm  # Human documentation is tested separately; request rules come from code.
        reference = compute_reference(scenario)
        payload = build_tool_context(reference)
        return (
            f"{build_decision_protocol()}\n\n"
            "AUTHORITATIVE DECISION ENVELOPE (copy exactly):\n"
            f"{json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n\n"
            "Return only status, stops, and reviews according to the schema. "
            "Do not return the financial report; the system attaches it deterministically.\n"
        )

    @staticmethod
    def _remove_schema_keyword(value: Any, keyword: str) -> None:
        """Remove one unsupported JSON Schema keyword recursively in a transport copy."""
        if isinstance(value, dict):
            value.pop(keyword, None)
            for nested in value.values():
                LLMTestRunner._remove_schema_keyword(nested, keyword)
        elif isinstance(value, list):
            for nested in value:
                LLMTestRunner._remove_schema_keyword(nested, keyword)

    @staticmethod
    def _transport_schema(strip_unique: bool) -> dict[str, Any]:
        """Build a provider-compatible copy without weakening local validation."""
        schema: dict[str, Any] = deepcopy(DECISION_JSON_SCHEMA)
        if strip_unique:
            LLMTestRunner._remove_schema_keyword(schema, "uniqueItems")
        return schema

    def request_spec(self, prompt: str, config: VCRConfig) -> LLMRequestSpec:
        profile = config.profile
        if profile.response_format_type == "json_object":
            response_format: dict[str, Any] = {"type": "json_object"}
            system_prompt = (
                SYSTEM_PROMPT
                + "\n\nOczekiwany strict JSON Schema:\n"
                + json.dumps(DECISION_JSON_SCHEMA["schema"], ensure_ascii=False, indent=2)
            )
        elif profile.response_format_type == "json_schema":
            transport = self._transport_schema(profile.strip_unique_items_for_transport)
            response_format = {"type": "json_schema", "json_schema": transport}
            system_prompt = SYSTEM_PROMPT
        else:  # ModelProfile already rejects this; keep the runner fail-closed as well.
            raise ValueError(f"unsupported response_format_type={profile.response_format_type!r}")
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

    def parse_decision(self, content: str) -> dict[str, Any]:
        try:
            parsed = json.loads(content.strip())
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

        stop_codes = set(STOP_FACT_TO_CODE.values())
        review_codes = set(REVIEW_FACT_TO_CODE.values())
        invalid_stops = set(parsed["stops"]) - stop_codes
        invalid_reviews = set(parsed["reviews"]) - review_codes
        if invalid_stops:
            raise ValueError(
                "decision contains non-STOP codes in stops: " + ", ".join(sorted(invalid_stops))
            )
        if invalid_reviews:
            raise ValueError(
                "decision contains non-REVIEW codes in reviews: "
                + ", ".join(sorted(invalid_reviews))
            )
        expected_status = "STOPPED" if parsed["stops"] else "FINAL"
        if parsed["status"] != expected_status:
            raise ValueError(
                f"decision status {parsed['status']!r} is inconsistent with stops; "
                f"expected {expected_status!r}"
            )
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
        output_dir = RESPONSE_ROOT / model_slug
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "raw_response": response.content,
            "parsed_response": parsed,
            "metadata": {
                "request_id": response.request_id,
                "requested_model": response.requested_model,
                "returned_model": response.returned_model,
                "finish_reason": response.finish_reason,
                "native_finish_reason": response.native_finish_reason,
                "system_fingerprint": response.system_fingerprint,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
                "cost": response.cost,
            },
        }
        (output_dir / f"{scenario_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
