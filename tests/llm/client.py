from __future__ import annotations

import time
from os import environ

import requests

# OpenRouter API base URL
OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"


class LLMClient:
    def __init__(self, require_api_key: bool = True):
        api_key = environ.get("OPENROUTER_API_KEY")
        if require_api_key and not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        self.api_key = api_key
        self.model_name = environ.get("LLM_MODEL") or "google/gemini-3.5-flash"

    def call(self, system_prompt: str, user_prompt: str, timeout: int = 120, json_schema: dict | None = None) -> str:  # noqa: E501
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 16000,
        }
        if json_schema:
            payload["response_format"] = {"type": "json_schema", "json_schema": json_schema}
        else:
            payload["response_format"] = {"type": "json_object"}

        response = requests.post(
            OPENROUTER_BASE,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def call_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        retries: int = 2,
        delay: int = 15,
        timeout: int = 120,
        json_schema: dict | None = None,
    ) -> str:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                return self.call(system_prompt, user_prompt, timeout=timeout, json_schema=json_schema)  # noqa: E501
            except Exception as exc:
                last_exc = exc
                if attempt < retries:
                    print(f"[LLMClient] attempt {attempt + 1} failed: {exc}. Retrying in {delay}s...")  # noqa: E501
                    time.sleep(delay)
        raise last_exc
