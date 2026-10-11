"""PDF to text, as in the organisers' tutorial (PyMuPDF get_text).

Only the newline convention is normalised. Accents, punctuation and every
space, including the one PyMuPDF leaves at the end of each line, are kept,
because the output check compares the model's answer with this text.
"""
from pathlib import Path

import pymupdf

from . import SUBMISSION

DEFAULT_PDF = SUBMISSION.parent / "raw_data" / "document_to_anonymize.pdf"
RAW_DOCUMENT = SUBMISSION / "raw_uncensored_document.txt"


def extract_pdf(pdf_path: Path, out_path: Path = None) -> str:
    """Extract every page and write the text to out_path."""
    with pymupdf.open(pdf_path) as doc:
        text = "".join(page.get_text() for page in doc)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    Path(out_path or RAW_DOCUMENT).write_bytes(text.encode("utf-8"))
    return text
