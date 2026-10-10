import time
from typing import Protocol, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from submission.anonymizer import config

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    def generate_json(self, prompt: str, schema: type[T]) -> T: ...

    def generate_text(self, prompt: str) -> str: ...


class GeminiClient:
    """Gemini via google-genai, retrying rate-limit and server errors."""

    def __init__(self, model: str, temperature: float = config.TEMPERATURE,
                 sleep=time.sleep):
        self.model = model
        self.temperature = temperature
        self._sleep = sleep
        self._client = genai.Client(api_key=config.api_key())

    def generate_json(self, prompt: str, schema: type[T]) -> T:
        response = self._generate(prompt, types.GenerateContentConfig(
            temperature=self.temperature,
            response_mime_type="application/json",
            response_schema=schema,
        ))
        # Validating ourselves (instead of response.parsed) makes a bad
        # reply raise pydantic's ValidationError rather than return None.
        return schema.model_validate_json(response.text)

    def generate_text(self, prompt: str) -> str:
        response = self._generate(prompt, types.GenerateContentConfig(
            temperature=self.temperature,
        ))
        return response.text

    def _generate(self, prompt: str, generation_config):
        for attempt in range(config.MAX_RETRIES + 1):
            try:
                return self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=generation_config,
                )
            except Exception as error:
                if getattr(error, "code", None) not in config.RETRY_CODES:
                    raise

                if attempt == config.MAX_RETRIES:
                    raise RuntimeError(
                        f"Gemini failed after retries: {error}"
                    ) from error

                self._sleep(2 ** attempt)
