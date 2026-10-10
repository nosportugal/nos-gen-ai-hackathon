"""Deterministic masking. Owner: feature/anonymization.

The detector points at spans (line + exact text). This module finds each
span in its line, works out which words it touches and turns each of those
words into a single "*". Lines, spacing and every other word stay byte for
byte the same. How a "*" is finally shown (as is, blurred, a random
value...) is up to the client, which can locate every "*" through
mask_with_positions().
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from anonymizer.spans import Category, Span

MASK = "*"

# Sentence punctuation around a word is kept, so "(João," becomes "(*,".
EDGE_PUNCTUATION = ",.;:!?()[]{}\"'«»“”‘’"

_WORD = re.compile(r"\S+")

# Letters, digits and the accents of decomposed text ("e" + U+0301).
_WORD_CHAR = r"[\ẁ-ͯ]"


@dataclass(frozen=True)
class MaskedWord:
    """Where one "*" sits in the masked text (line is 1-based)."""

    line: int
    column: int
    category: Category


@dataclass(frozen=True)
class MaskResult:
    """The masked text, every "*" put in it, and the spans not found."""

    text: str
    words: List[MaskedWord]
    unmatched: List[Span]


def mask(text: str, spans: Sequence[Span],
         keep_punctuation: bool = True) -> str:
    """Replace every word touched by a span with a single "*".

    "Ana Correia" becomes "* *". The number of lines and words must not
    change, and words outside the spans must stay byte for byte the same.
    With keep_punctuation=False, "Santos," becomes "*" instead of "*,".
    A token made only of punctuation, such as a lone "«", is not a word
    and stays as it is.
    """
    return mask_with_positions(text, spans, keep_punctuation).text


def mask_with_positions(text: str, spans: Sequence[Span],
                        keep_punctuation: bool = True) -> MaskResult:
    """Same as mask(), plus the position and category of every "*"."""
    lines = text.split("\n")
    hits: Dict[int, List[Tuple[int, int, Category]]] = {}
    unmatched = []
    for span in spans:
        found = _find(lines, span)
        if not found:
            unmatched.append(span)
        for index, start, end in found:
            hits.setdefault(index, []).append((start, end, span.category))

    words: List[MaskedWord] = []
    for index in sorted(hits):
        lines[index] = _mask_line(
            lines[index], index + 1, hits[index], keep_punctuation, words,
        )
    return MaskResult("\n".join(lines), words, unmatched)


def _find(lines: List[str], span: Span) -> List[Tuple[int, int, int]]:
    """(line index, start, end) of every occurrence of the span.

    Looks in the span's own line first; if the text is not there, it may
    run over a line break, so the line is also tried joined with the next
    one and with the previous one.
    """
    text = " ".join(span.text.split()).strip(EDGE_PUNCTUATION + " ")
    words = text.split()
    index = span.line - 1
    if not words or not 0 <= index < len(lines):
        return []
    pattern = _pattern(words)
    found = [(index,) + m.span(1) for m in pattern.finditer(lines[index])]
    if found:
        return found
    for first in (index, index - 1):
        if 0 <= first < len(lines) - 1:
            found += _across_break(lines, first, pattern)
    return found


def _pattern(words: Sequence[str]) -> re.Pattern:
    """Every occurrence of the words in order, as whole words.

    Any whitespace may separate the words, so a name still matches when
    the PDF put two spaces or a line break between them; "2" never
    matches inside "12". The pattern is a lookahead, so overlapping
    occurrences ("912 912" in "912 912 912") are all found: read each
    one with match.span(1).
    """
    body = r"\s+".join(re.escape(word) for word in words)
    if re.match(_WORD_CHAR, words[0]):
        body = "(?<!" + _WORD_CHAR + ")" + body
    if re.search(_WORD_CHAR + "$", words[-1]):
        body += "(?!" + _WORD_CHAR + ")"
    return re.compile("(?=(" + body + "))")


def _across_break(lines: List[str], first: int,
                  pattern: re.Pattern) -> List[Tuple[int, int, int]]:
    """Occurrences that start on line `first` and end on the next one."""
    cut = len(lines[first])
    joined = lines[first] + "\n" + lines[first + 1]
    found = []
    for match in pattern.finditer(joined):
        start, end = match.span(1)
        if start < cut < end:
            found += [(first, start, cut), (first + 1, 0, end - cut - 1)]
    return found


def _mask_line(line: str, number: int,
               hits: List[Tuple[int, int, Category]],
               keep_punctuation: bool, words: List[MaskedWord]) -> str:
    """Turn every word of the line that a hit touches into a "*"."""
    out = []
    length = 0
    done = 0
    for match in _WORD.finditer(line):
        start, end = match.span()
        touching = [cat for lo, hi, cat in hits if lo < end and hi > start]
        if not touching:
            continue
        if keep_punctuation:
            start, end = _trim(line, start, end)
        if start == end:
            continue
        gap = line[done:start]
        out += [gap, MASK]
        words.append(MaskedWord(number, length + len(gap), touching[0]))
        length += len(gap) + len(MASK)
        done = end
    out.append(line[done:])
    return "".join(out)


def _trim(line: str, start: int, end: int) -> Tuple[int, int]:
    """Leave the sentence punctuation around a word out of the mask."""
    while start < end and line[start] in EDGE_PUNCTUATION:
        start += 1
    while end > start and line[end - 1] in EDGE_PUNCTUATION:
        end -= 1
    return start, end
