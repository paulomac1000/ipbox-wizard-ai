"""Small OpenRouter client used only by explicit LLM benchmark runs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from os import environ
from typing import Any

import requests

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"


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


class LLMClient:
    def __init__(self, require_api_key: bool = True):
        provider = environ.get("LLM_PROVIDER", "openrouter")
        if provider != "openrouter":
            raise ValueError("Only OpenRouter is supported by the benchmark client")
        self.api_key = environ.get("OPENROUTER_API_KEY")
        if require_api_key and not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")

    def call(self, payload: dict[str, Any], timeout: int = 180) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
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
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("OpenRouter returned no choices")
        choice = choices[0]
        message = choice.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            refusal = message.get("refusal")
            raise ValueError(f"LLM returned empty content; refusal={refusal!r}")
        usage = data.get("usage") or {}
        return LLMResponse(
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
        )

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
