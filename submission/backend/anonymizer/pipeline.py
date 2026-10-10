"""Glue between the three steps, shared by the CLI and the API."""

from dataclasses import dataclass
from pathlib import Path
from typing import List

from anonymizer import detector, extract, masker
from anonymizer.spans import Span


@dataclass(frozen=True)
class Analysis:
    """Extracted text plus the spans the LLM flagged in it."""

    text: str
    spans: List[Span]


def analyze(pdf_path: Path) -> Analysis:
    """Extract the text and detect sensitive spans, without masking.

    Split from masking so a reviewer can accept or reject spans first.
    """
    text = extract.extract_text(pdf_path)
    return Analysis(text=text, spans=detector.detect(text))


def anonymize(pdf_path: Path) -> str:
    """Full run with no manual review: extract, detect, mask."""
    analysis = analyze(pdf_path)
    return masker.mask(analysis.text, analysis.spans)
