"""Which words of a file were masked in its masked version.

Every maskable word of the source gets an id "L<line>:W<word>": its line
number in the source file (blank lines counted, as in an editor) and its
position on that line. Masking replaces one word with one asterisk, so
the same id points at the same word in the source, in an agent's output
and in a ground-truth file. That is what lets a scorer compare them.

    {"L3:W2": {"text": "Ana-Maria", "start": 57, "end": 66,
               "masked": true}, ...}

start/end are character offsets of the word in the source. masked is
true (the word became mask(word), or a bare "*" that also hid its
punctuation, as some references do), false, or null when the masked
file breaks the rules at that word
(run mask_syntax_validation first; after a missing or extra line the ids of the
following lines can no longer be matched).

Usage:
    python -m benchmark.mask_diff file.txt file_masked.txt
"""
import json
import sys

try:
    from .mask_syntax_validation import SPLIT, mask, masked_lines, read
    from .mask_syntax_validation import source_lines
except ImportError:  # run as a plain script
    from mask_syntax_validation import SPLIT, mask, masked_lines, read
    from mask_syntax_validation import source_lines


def line_offsets(text: str) -> dict:
    """Character offset where each line (1-based) starts."""
    offsets, pos = {}, 0
    for n, line in enumerate(text.split("\n"), 1):
        offsets[n] = pos
        pos += len(line) + 1
    return offsets


def mask_diff(source: str, masked: str) -> dict:
    starts = line_offsets(source)
    out = masked_lines(masked)
    words = {}
    for k, (line_no, src) in enumerate(source_lines(source)):
        # Spaces at the end of a line may be kept or dropped.
        src_parts = SPLIT.split(src.rstrip())
        out_parts = SPLIT.split(out[k].rstrip()) if k < len(out) else []
        aligned = len(out_parts) == len(src_parts)
        pos, word_no = starts[line_no], 0
        for i, part in enumerate(src_parts):
            if i % 2 == 0 and part:
                word_no += 1  # every word counts, maskable or not
            if i % 2 == 0 and part and mask(part) is not None:
                masked_flag = None
                if aligned and out_parts[i] == part:
                    masked_flag = False
                elif aligned and out_parts[i] in (mask(part), "*"):
                    masked_flag = True
                words[f"L{line_no}:W{word_no}"] = {
                    "text": part, "start": pos, "end": pos + len(part),
                    "masked": masked_flag,
                }
            pos += len(part)
    return words


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(__doc__)
        return 2
    print(json.dumps(mask_diff(read(args[0]), read(args[1])),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
