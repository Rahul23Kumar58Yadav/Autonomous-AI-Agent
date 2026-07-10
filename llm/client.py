

import os
import time
import logging
import httpx
from groq import Groq

logger = logging.getLogger("llm.client")


class LLMClient:
    def __init__(self, model: str = "llama-3.1-8b-instant", max_retries: int = 3):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment.")
        self.client = Groq(api_key=api_key, http_client=httpx.Client())

        self.model = model
        self.max_retries = max_retries

    def complete(self, prompt: str, system: str = None) -> str:
        """Calls the LLM with retry + exponential backoff (resilience)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.4,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call failed (attempt {attempt}): {e}")
                time.sleep(1.5 * attempt)

        raise RuntimeError(f"LLM call failed after {self.max_retries} attempts: {last_error}")