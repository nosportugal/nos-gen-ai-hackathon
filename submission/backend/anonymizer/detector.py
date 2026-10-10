"""LLM detection of sensitive data. Owner: feature/gemini-detection."""

import re
from pathlib import Path
from typing import List

from pydantic import BaseModel

from anonymizer import gemini_client
from anonymizer.spans import Category, Span

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompt.txt"
PLACEHOLDER = "{{DOCUMENT}}"


class DetectedSpan(BaseModel):
    line: int
    text: str
    category: Category
    reason: str


class Detection(BaseModel):
    spans: List[DetectedSpan]


def number_lines(text: str) -> str:
    """Prefix each line with "L001| " so the LLM can point at lines."""
    return "\n".join(
        f"L{i:03d}| {line}"
        for i, line in enumerate(text.split("\n"), start=1)
    )


def build_prompt(text: str) -> str:
    """prompt.txt with the numbered document in place of the placeholder."""
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace(PLACEHOLDER, number_lines(text))


def _locate(found: List[DetectedSpan], lines: List[str]) -> List[Span]:
    """Keep spans whose text really is in the document.

    If the LLM got the line number wrong, use the nearest line that
    contains the text as whole words; drop spans that appear nowhere.
    """
    spans = []
    seen = set()
    for item in found:
        text = item.text.strip()
        if not text:
            continue
        word = re.compile(r"(?<!\w)" + re.escape(text) + r"(?!\w)")
        candidates = [
            i for i, line in enumerate(lines, 1) if word.search(line)
        ]
        if not candidates:
            continue
        line = min(candidates, key=lambda i: abs(i - item.line))
        key = (line, text, item.category)
        if key in seen:
            continue
        seen.add(key)
        spans.append(Span(line, text, item.category, item.reason))
    return spans


def detect(text: str) -> List[Span]:
    """Ask Gemini which parts of the text are sensitive.

    The LLM only points at spans; it never rewrites the document, so the
    formatting cannot drift. Each span must match its line exactly.
    """
    detection = gemini_client.generate_json(build_prompt(text), Detection)
    return _locate(detection.spans, text.split("\n"))
