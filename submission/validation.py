import json
import os
import re
from typing import Any

import requests


API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def call_api(prompt_text: str, temperature: float = 0.0) -> dict[str, Any]:
    """Send a prompt to the configured validation model."""
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY environment variable is not set")

    validation_model = os.getenv("VALIDATION_MODEL")
    if not validation_model:
        raise RuntimeError("VALIDATION_MODEL environment variable is not set")

    response = requests.post(
        f"{API_BASE_URL}/{validation_model}:generateContent",
        params={"key": api_key},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": temperature},
        },
        timeout=60,
    )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError("The API response must be a JSON object")
    return result


class DocumentValidator:
    """Validate meaning preservation and the number of masked words."""

    def entailment(self, original_document: str, last_document: str) -> int:
        """Score how well the anonymized document preserves the original content."""
        prompt = f"""
Compare the original document with the anonymized document below.
Score from 0 to 100 how well the anonymized document preserves the original
document's context, meaning, and structure. A score of 100 means the content
is fully preserved apart from appropriate anonymization. A score of 0 means
the content is not preserved. Masked sensitive words represented by one or
more asterisks are expected and should not reduce the score by themselves.

Return only valid JSON in this exact format:
{{"score": 0}}
The score must be an integer between 0 and 100.

Original document:
{original_document}

Anonymized document:
{last_document}
""".strip()

        response = call_api(prompt)
        response_text = self._response_text(response)
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as error:
            raise ValueError("The entailment response was not valid JSON") from error

        score = result.get("score") if isinstance(result, dict) else None
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
            raise ValueError('The entailment response must contain an integer "score" from 0 to 100')
        return score

    def check_removed_words(self, document: str, expected_count: int) -> bool:
        """Check whether the document contains the expected number of masked words."""
        if expected_count < 0:
            raise ValueError("expected_count must not be negative")

        masked_words = re.findall(r"\*+", document)
        return len(masked_words) == expected_count

    @staticmethod
    def _response_text(response: dict[str, Any]) -> str:
        try:
            parts = response["candidates"][0]["content"]["parts"]
            text = parts[0]["text"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError("The API response did not contain generated text") from error

        if not isinstance(text, str):
            raise ValueError("The generated response text must be a string")
        return text.strip()
