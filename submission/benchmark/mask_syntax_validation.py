"""Check that a masked file follows the masking rules.

It does not judge which words were masked, only how:
- each word is either unchanged or replaced by exactly one asterisk,
  keeping the punctuation around it (see mask());
- spacing, line breaks and every other character are unchanged, except
  spaces at the end of a line, which may be kept or dropped;
- blank lines are removed and no other line is added, removed or joined.

Usage:
    python -m benchmark.mask_syntax_validation file.txt file_masked.txt

Prints a JSON report. Exit code 0 when the rules hold, 1 otherwise.
"""
import json
import re
import sys
from pathlib import Path

# A masked word keeps this punctuation around its asterisk.
OPEN_PUNCT = "([{\"'«“‘"
CLOSE_PUNCT = ")]}\"'»”’,;:!?."
SPLIT = re.compile(r"(\s+)")  # keeps the whitespace between words


def mask(word: str):
    """The masked form of a word, or None if it has nothing to mask."""
    i = 0
    while i < len(word) and word[i] in OPEN_PUNCT:
        i += 1
    j = len(word)
    while j > i and word[j - 1] in CLOSE_PUNCT:
        j -= 1
    if not any(ch.isalnum() for ch in word[i:j]):
        return None
    return word[:i] + "*" + word[j:]


def source_lines(text: str) -> list:
    """(line number in the file, line) for every non-blank line."""
    return [(n, ln) for n, ln in enumerate(text.split("\n"), 1)
            if ln.strip()]


def masked_lines(text: str) -> list:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # a final newline is optional
    return lines


def check_line(src: str, out: str):
    """The first rule broken on one line, or None."""
    src_parts, out_parts = SPLIT.split(src), SPLIT.split(out)
    if len(src_parts) != len(out_parts):
        return "words added, removed, joined or split"
    for k, (s, o) in enumerate(zip(src_parts, out_parts)):
        if s == o:
            continue
        if k % 2:
            return "spacing changed"
        if o != mask(s):
            return f"word changed: {s!r} -> {o!r}"
    return None


def validate(source: str, masked: str) -> dict:
    src = [ln.rstrip() for _, ln in source_lines(source)]
    out = [ln.rstrip() for ln in masked_lines(masked)]
    problems = []
    if "\r" in masked:
        problems.append("contains carriage returns")
    if len(out) != len(src):
        problems.append(f"{len(out)} lines, expected {len(src)}")
    for n, (s, o) in enumerate(zip(src, out), 1):
        problem = "blank line kept" if not o.strip() else check_line(s, o)
        if problem:
            problems.append(f"masked line {n}: {problem}")
    return {"valid": not problems, "problems": problems}


def compare_word_counts(source: str, masked: str) -> int:
    """Report per-line counts, ignoring blanks and normalising newlines.

    This compatibility check accepts changed words and spacing. Use validate()
    separately to enforce the masking syntax.
    """
    original = [ln for ln in source.splitlines() if ln.strip()]
    answer = [ln for ln in masked.splitlines() if ln.strip()]
    if not answer:
        print("submission.txt is empty")
        return 1
    if len(original) != len(answer):
        print(f"line count differs: {len(original)} vs {len(answer)}")
        return 1
    bad = 0
    for number, (a, b) in enumerate(zip(original, answer), 1):
        if len(a.split()) != len(b.split()):
            bad += 1
            print(f"line {number}: {len(a.split())} words -> "
                  f"{len(b.split())}")
            print(f"  original: {a.strip()}")
            print(f"  answer:   {b.strip()}")
    masked = sum(line.count("*") for line in answer)
    print(f"{len(original) - bad} of {len(original)} lines aligned, "
          f"{masked} asterisks")
    return 1 if bad else 0


def read(path) -> str:
    """Read exactly: no newline translation, trailing spaces kept."""
    return Path(path).read_bytes().decode("utf-8")


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(__doc__)
        return 2
    result = validate(read(args[0]), read(args[1]))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
