"""LLM detection of sensitive data. Owner: feature/gemini-detection."""

from typing import List

from anonymizer.spans import Span


def detect(text: str) -> List[Span]:
    """Ask Gemini which parts of the text are sensitive.

    The LLM only points at spans; it never rewrites the document, so the
    formatting cannot drift. Each span must match its line exactly.
    """
    raise NotImplementedError("detect: feature/gemini-detection")
