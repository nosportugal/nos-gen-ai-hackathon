"""PDF to text. Owner: feature/pdf-processing."""

from pathlib import Path


def extract_text(pdf_path: Path) -> str:
    """Return the document text with PyMuPDF.

    Lines are separated by "\\n" and empty lines are removed; everything
    else stays as extracted, because the output must keep the formatting.
    """
    raise NotImplementedError("extract_text: feature/pdf-processing")
