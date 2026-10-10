"""PDF text extraction using PyMuPDF."""

from pathlib import Path

import pymupdf


def extract_text(pdf_path: Path) -> str:
    """Extract PDF text while removing empty lines."""

    if not pdf_path.is_file():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    lines = []

    with pymupdf.open(str(pdf_path)) as document:
        for page in document:
            page_text = page.get_text("text", sort=False)

            for line in page_text.splitlines():
                if line.strip():
                    lines.append(line)

    if not lines:
        raise ValueError(
            "PDF contains no extractable text."
        )

    return "\n".join(lines)
