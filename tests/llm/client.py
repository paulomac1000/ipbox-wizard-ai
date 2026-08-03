"""Small OpenRouter client used only by explicit LLM benchmark runs."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from os import environ
from typing import Any

import requests

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"


class PaidCostLimitError(RuntimeError):
    """Raised when a paid pytest run reaches or exceeds its declared budget."""


class PaidCostGuard:
    """Process-local paid-cost accounting shared by the session-scoped client."""

    def __init__(self, per_model_limit: float, total_limit: float) -> None:
        self.per_model_limit = self._positive("LLM_MAX_COST_PER_MODEL_USD", per_model_limit)
        self.total_limit = self._positive("LLM_MAX_TOTAL_COST_USD", total_limit)
        self.model_costs: dict[str, float] = {}
        self.total_cost = 0.0
        self._exceeded_message: str | None = None

    @staticmethod
    def _positive(name: str, value: object) -> float:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be a finite positive number")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be a finite positive number") from exc
        if not math.isfinite(number) or number <= 0:
            raise ValueError(f"{name} must be a finite positive number")
        return number

    @staticmethod
    def _cost(value: object) -> float:
        if isinstance(value, bool):
            raise PaidCostLimitError("provider response cost must be a finite non-negative number")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise PaidCostLimitError(
                "provider response cost must be a finite non-negative number"
            ) from exc
        if not math.isfinite(number) or number < 0:
            raise PaidCostLimitError("provider response cost must be a finite non-negative number")
        return number

    @classmethod
    def from_environment(cls) -> PaidCostGuard:
        return cls(
            environ.get("LLM_MAX_COST_PER_MODEL_USD"),
            environ.get("LLM_MAX_TOTAL_COST_USD"),
        )

    def require_request_allowed(self, model: str) -> None:
        if self._exceeded_message is not None:
            raise PaidCostLimitError(self._exceeded_message)
        model_cost = self.model_costs.get(model, 0.0)
        if model_cost >= self.per_model_limit:
            raise PaidCostLimitError(
                f"paid cost limit reached for {model}: "
                f"${model_cost:.6f} / ${self.per_model_limit:.6f}"
            )
        if self.total_cost >= self.total_limit:
            raise PaidCostLimitError(
                f"total paid cost limit reached: ${self.total_cost:.6f} / ${self.total_limit:.6f}"
            )

    def block_unaccounted_response(self, reason: str) -> None:
        self._exceeded_message = (
            "paid response could not be cost-accounted fail-closed: "
            f"{reason}. No further provider request is allowed."
        )

    def account_cost(self, model: str, value: object) -> None:
        try:
            cost = self._cost(value)
        except PaidCostLimitError as exc:
            self.block_unaccounted_response(str(exc))
            return
        model_cost = self.model_costs.get(model, 0.0) + cost
        total_cost = self.total_cost + cost
        if not math.isfinite(model_cost) or not math.isfinite(total_cost):
            raise PaidCostLimitError("paid cost accumulation overflowed")
        self.model_costs[model] = model_cost
        self.total_cost = total_cost

        violations: list[str] = []
        if model_cost > self.per_model_limit:
            violations.append(f"{model} paid ${model_cost:.6f} > ${self.per_model_limit:.6f}")
        if total_cost > self.total_limit:
            violations.append(f"total paid ${total_cost:.6f} > ${self.total_limit:.6f}")
        if violations:
            self._exceeded_message = (
                "paid cost guard exceeded after accounting the latest response; "
                + "; ".join(violations)
                + ". No further provider request is allowed."
            )

    def raise_if_exceeded(self) -> None:
        if self._exceeded_message is not None:
            raise PaidCostLimitError(self._exceeded_message)


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: str
    request_id: str | None
    requested_model: str
    returned_model: str | None
    finish_reason: str | None
    native_finish_reason: str | None
    system_fingerprint: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost: float | None
    provider_error: str | None = None


class LLMClient:
    def __init__(
        self,
        require_api_key: bool = True,
        *,
        enforce_cost_limits: bool = False,
    ):
        provider = environ.get("LLM_PROVIDER", "openrouter")
        if provider != "openrouter":
            raise ValueError("Only OpenRouter is supported by the benchmark client")
        self.api_key = environ.get("OPENROUTER_API_KEY")
        if require_api_key and not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        self.cost_guard = PaidCostGuard.from_environment() if enforce_cost_limits else None

    def call(self, payload: dict[str, Any], timeout: int = 180) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        model = str(payload["model"])
        if self.cost_guard is not None:
            self.cost_guard.require_request_allowed(model)
        response = requests.post(
            OPENROUTER_BASE,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/paulomac1000/ipbox-wizard-ai",
                "X-Title": "ipbox-wizard-ai model benchmark",
            },
            json=payload,
            timeout=timeout,
        )
        http_error: requests.HTTPError | None = None
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            http_error = exc
        try:
            data = response.json()
        except (TypeError, ValueError) as exc:
            if self.cost_guard is not None:
                self.cost_guard.block_unaccounted_response("provider returned invalid JSON")
            if http_error is not None:
                raise http_error from exc
            raise
        if not isinstance(data, dict):
            if self.cost_guard is not None:
                self.cost_guard.block_unaccounted_response("provider JSON root is not an object")
            if http_error is not None:
                raise http_error
            raise ValueError("OpenRouter response root must be an object")
        usage = data.get("usage") or {}
        if not isinstance(usage, dict):
            usage = {}
        if self.cost_guard is not None:
            self.cost_guard.account_cost(model, usage.get("cost"))
        if http_error is not None:
            raise http_error
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("OpenRouter returned no choices")
        choice = choices[0]
        message = choice.get("message") or {}
        raw_content = message.get("content")
        refusal = message.get("refusal")
        provider_error: str | None = None
        if isinstance(raw_content, str):
            content = raw_content
            if not content.strip():
                provider_error = (
                    f"empty content; refusal={refusal!r}"
                    if refusal is not None
                    else "empty content"
                )
        else:
            content = ""
            provider_error = (
                f"non-string content; refusal={refusal!r}"
                if refusal is not None
                else f"non-string content: {type(raw_content).__name__}"
            )
        result = LLMResponse(
            content=content,
            request_id=data.get("id") or response.headers.get("x-request-id"),
            requested_model=str(payload["model"]),
            returned_model=data.get("model"),
            finish_reason=choice.get("finish_reason"),
            native_finish_reason=choice.get("native_finish_reason"),
            system_fingerprint=data.get("system_fingerprint"),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            cost=usage.get("cost"),
            provider_error=provider_error,
        )
        return result

    def raise_if_cost_limit_exceeded(self) -> None:
        if self.cost_guard is not None:
            self.cost_guard.raise_if_exceeded()

    @staticmethod
    def _retry_after_seconds(response: requests.Response | None) -> float | None:
        if response is None:
            return None
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
            except (TypeError, ValueError, OverflowError):
                return None
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())

    def call_with_retry(
        self,
        payload: dict[str, Any],
        *,
        retries: int = 2,
        delay: int = 10,
        timeout: int = 180,
    ) -> LLMResponse:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            sleep_seconds: float | None = None
            try:
                return self.call(payload, timeout=timeout)
            except requests.HTTPError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else None
                if status not in {429, 503} or attempt == retries:
                    raise
                sleep_seconds = self._retry_after_seconds(exc.response)
            except requests.ConnectTimeout as exc:
                last_error = exc
                if attempt == retries:
                    raise
            if attempt < retries:
                time.sleep(sleep_seconds if sleep_seconds is not None else delay * (attempt + 1))
        assert last_error is not None
        raise last_error
