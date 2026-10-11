"""Compatibility command for per-line word counts.

Run from submission/: python check_submission.py.
For masking syntax, use python -m benchmark.mask_syntax_validation.
"""
import sys
from pathlib import Path

from benchmark.mask_syntax_validation import compare_word_counts

HERE = Path(__file__).resolve().parent


def lines(path):
    """Keep the existing helper's newline and blank-line behaviour."""
    text = path.read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line.strip()]


def main() -> int:
    original = "\n".join(lines(HERE / "raw_uncensored_document.txt"))
    answer = "\n".join(lines(HERE / "submission.txt"))
    return compare_word_counts(original, answer)


if __name__ == "__main__":
    sys.exit(main())
