"""CLI: python -m anonymizer <pdf> [-o <output>]"""

import argparse
import sys
from pathlib import Path

from anonymizer.pipeline import anonymize


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="anonymizer",
        description="Mask sensitive data in a PDF, one * per word.",
    )
    parser.add_argument("pdf", type=Path, help="document to anonymize")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="write the masked text here instead of stdout",
    )
    args = parser.parse_args(argv)

    masked = anonymize(args.pdf)
    if args.output:
        args.output.write_text(masked, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(masked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
