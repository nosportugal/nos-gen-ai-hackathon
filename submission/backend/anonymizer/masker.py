"""Deterministic masking. Owner: feature/anonymization."""

from typing import Sequence

from anonymizer.spans import Span


def mask(text: str, spans: Sequence[Span]) -> str:
    """Replace every word touched by a span with a single "*".

    "Ana Correia" becomes "* *". The number of lines and words must not
    change, and words outside the spans must stay byte for byte the same.
    """
    raise NotImplementedError("mask: feature/anonymization")
