"""Source model: lines, word components, offsets and the masking rule.

Coordinates are zero-based Python code-point offsets into the canonical
source, half-open intervals [start, end).

Frozen provisional rules implemented here (see the policy file):
- Lines are separated by LF. One final LF does not create an extra line.
- A line that is empty or whitespace-only is a blank line and is removed.
- A word (component) is a maximal run of non-whitespace characters that
  contains at least one alphanumeric character.
- Masking replaces the word's core with one asterisk. Opening punctuation
  at the start and closing punctuation at the end stay; everything between
  them (hyphens, slashes, dots, at-signs, currency signs, units) is core.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MASK = "*"
DEFAULT_OPEN = "([{\"'«“‘"
DEFAULT_CLOSE = ")]}\"'»”’,;:!?."
TOKEN_RE = re.compile(r"\S+")


@dataclass(frozen=True)
class Token:
    line: int  # 1-based retained line number
    index: int  # 1-based position within the line
    start: int
    end: int
    core_start: int
    core_end: int
    text: str
    prefix: str
    core: str
    suffix: str
    maskable: bool

    @property
    def comp_id(self) -> str:
        return f"L{self.line:03d}.T{self.index:02d}"

    @property
    def masked_form(self) -> str:
        return self.prefix + MASK + self.suffix


@dataclass(frozen=True)
class Line:
    source_index: int  # 0-based index among all source lines
    start: int
    end: int  # excludes the newline
    text: str
    retained_no: int  # 1-based among retained lines, 0 when removed


def split_lines(text: str) -> list:
    """Split on LF; a single final LF is not an extra line."""
    if text == "":
        return []
    parts = text.split("\n")
    if parts[-1] == "":
        parts.pop()
    return parts


def is_blank(line: str) -> bool:
    return line == "" or line.isspace()


def split_token(text: str, open_p: str, close_p: str):
    """Return (prefix, core, suffix, maskable) for one token."""
    i = 0
    while i < len(text) and text[i] in open_p:
        i += 1
    j = len(text)
    while j > i and text[j - 1] in close_p:
        j -= 1
    core = text[i:j]
    maskable = any(ch.isalnum() for ch in core)
    return text[:i], core, text[j:], maskable


class SourceDoc:
    """Canonical source with a position map across blank-line removal."""

    def __init__(self, text, open_p=DEFAULT_OPEN, close_p=DEFAULT_CLOSE):
        if "\r" in text:
            raise ValueError("canonical source must use LF newlines only")
        self.text = text
        self.open_p = open_p
        self.close_p = close_p
        self.final_newline = text.endswith("\n")
        self.lines = []
        self.retained = []
        self.tokens = []
        self.line_tokens = {}
        self._by_id = {}
        pos = 0
        for idx, raw in enumerate(split_lines(text)):
            start, end = pos, pos + len(raw)
            pos = end + 1
            keep = not is_blank(raw)
            number = len(self.retained) + 1 if keep else 0
            line = Line(idx, start, end, raw, number)
            self.lines.append(line)
            if keep:
                self.retained.append(line)
                self._tokenize(line)

    def _tokenize(self, line: Line) -> None:
        toks = []
        for k, m in enumerate(TOKEN_RE.finditer(line.text), 1):
            text = m.group(0)
            prefix, core, suffix, maskable = split_token(
                text, self.open_p, self.close_p
            )
            start = line.start + m.start()
            tok = Token(
                line=line.retained_no,
                index=k,
                start=start,
                end=line.start + m.end(),
                core_start=start + len(prefix),
                core_end=start + len(prefix) + len(core),
                text=text,
                prefix=prefix,
                core=core,
                suffix=suffix,
                maskable=maskable,
            )
            toks.append(tok)
            self._by_id[tok.comp_id] = tok
        self.line_tokens[line.retained_no] = toks
        self.tokens.extend(toks)

    # -- lookups ---------------------------------------------------------
    def token(self, comp_id: str) -> Token:
        return self._by_id[comp_id]

    def get(self, line: int, index: int):
        toks = self.line_tokens.get(line)
        if not toks or not 1 <= index <= len(toks):
            return None
        return toks[index - 1]

    @property
    def components(self) -> list:
        """Maskable tokens only: the unit of every accuracy metric."""
        return [t for t in self.tokens if t.maskable]

    def source_map(self) -> dict:
        """Map retained line numbers back to source lines and offsets."""
        return {
            "coordinates": "zero-based code-point offsets, half-open",
            "source_line_count": len(self.lines),
            "retained_line_count": len(self.retained),
            "removed_source_line_indexes": [
                ln.source_index for ln in self.lines if not ln.retained_no
            ],
            "retained": [
                {
                    "line": ln.retained_no,
                    "source_line_index": ln.source_index,
                    "start": ln.start,
                    "end": ln.end,
                }
                for ln in self.retained
            ],
        }

    # -- views -----------------------------------------------------------
    def token_index_view(self) -> str:
        """Numbered view given to ledger agents for locating words."""
        rows = []
        for ln in self.retained:
            toks = self.line_tokens[ln.retained_no]
            body = " ".join(f"[{t.index}]{t.text}" for t in toks)
            rows.append(f"L{ln.retained_no:03d}: {body}")
        return "\n".join(rows)

    def run_quotes(self, first: Token, last: Token) -> tuple:
        """The exact quotes accepted for a run of words on one line.

        Two come straight from the source (core-to-core and full). Two
        more are the same run as shown in the token index view, where
        words are separated by one space; they differ from the source
        forms only when the source has other spacing inside the run.
        """
        toks = self.line_tokens[first.line][first.index - 1:last.index]
        texts = [t.text for t in toks]
        if len(toks) == 1:
            view_core = first.core
        else:
            inner = texts[1:-1]
            view_core = " ".join(
                [first.core + first.suffix] + inner + [last.prefix + last.core]
            )
        return (
            self.text[first.core_start:last.core_end],
            self.text[first.start:last.end],
            view_core,
            " ".join(texts),
        )

    # -- rendering -------------------------------------------------------
    def render(self, mask_ids) -> str:
        """Deterministic rendering by source-coordinate replacement.

        Only the cores of the listed components change; blank lines are
        dropped; every other character is copied from the source.
        """
        mask_ids = set(mask_ids)
        unknown = [c for c in mask_ids if c not in self._by_id]
        if unknown:
            raise ValueError(f"unknown component ids: {sorted(unknown)[:5]}")
        out = []
        for ln in self.retained:
            text = ln.text
            for tok in reversed(self.line_tokens[ln.retained_no]):
                if tok.comp_id not in mask_ids:
                    continue
                if not tok.maskable:
                    raise ValueError(f"{tok.comp_id} is not maskable")
                a = tok.core_start - ln.start
                b = tok.core_end - ln.start
                text = text[:a] + MASK + text[b:]
            out.append(text)
        body = "\n".join(out)
        return body + "\n" if self.final_newline and out else body
