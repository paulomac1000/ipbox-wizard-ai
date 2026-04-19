import os
import time

import google.generativeai as genai


class LLMClient:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        genai.configure(api_key=api_key)

    def call(self, system_prompt: str, user_prompt: str, timeout: int = 120) -> str:
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            user_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=16000,
            ),
            request_options={"timeout": timeout},
        )
        return response.text

    def call_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        retries: int = 2,
        delay: int = 15,
        timeout: int = 120,
    ) -> str:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                return self.call(system_prompt, user_prompt, timeout=timeout)
            except Exception as exc:
                last_exc = exc
                if attempt < retries:
                    print(f"[LLMClient] attempt {attempt + 1} failed: {exc}. Retrying in {delay}s...")
                    time.sleep(delay)
        raise last_exc
