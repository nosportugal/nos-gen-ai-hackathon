import re
import time
from typing import Protocol, TypeVar

import httpx
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
                if _is_daily_quota(error):
                    # Retrying within seconds can't help: the quota only
                    # resets the next day.
                    raise RuntimeError(
                        f"Gemini daily quota exhausted: {error}"
                    ) from error

                if not _is_retryable(error):
                    raise

                if attempt == config.MAX_RETRIES:
                    raise RuntimeError(
                        f"Gemini failed after retries: {error}"
                    ) from error

                self._sleep(_retry_delay(error, attempt))


def _is_retryable(error: Exception) -> bool:
    # Dropped connections (e.g. Windows' WinError 10054) carry no HTTP
    # code, so they are recognised by type rather than by status.
    if isinstance(error, (ConnectionError, TimeoutError,
                          httpx.TransportError)):
        return True
    return getattr(error, "code", None) in config.RETRY_CODES


def _retry_delay(error: Exception, attempt: int) -> float:
    # A per-minute 429 says how long to wait ('retryDelay': '32s'); the
    # fixed 1/2/4 s backoff would retry too early and fail every time.
    match = re.search(r"'retryDelay': '(\d+(?:\.\d+)?)s'", str(error))
    if match:
        return min(float(match.group(1)), config.MAX_RETRY_DELAY)
    return 2 ** attempt


def _is_daily_quota(error: Exception) -> bool:
    return (getattr(error, "code", None) == 429
            and "PerDay" in str(error))
