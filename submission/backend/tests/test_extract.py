
from pathlib import Path

import pymupdf
import pytest

from anonymizer.extract import extract_text


def test_extract_text_from_pdf(tmp_path):
    """Verify that text can be extracted from a real PDF."""
    pdf_path = tmp_path / "test.pdf"

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Nome: Ana Correia")
        page.insert_text((72, 100), "Telefone: 912345678")
        document.save(str(pdf_path))

    result = extract_text(pdf_path)

    assert result.splitlines() == [
        "Nome: Ana Correia",
        "Telefone: 912345678",
    ]


def test_extract_multiple_pages(tmp_path):
    """Verify text extraction preserves page order."""
    pdf_path = tmp_path / "multiple_pages.pdf"

    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), "Pagina 1")
        document.new_page().insert_text((72, 72), "Pagina 2")
        document.save(str(pdf_path))

    result = extract_text(pdf_path)

    assert result.splitlines() == ["Pagina 1", "Pagina 2"]


def test_missing_pdf():
    """Verify that a missing file raises an error."""
    with pytest.raises(FileNotFoundError):
        extract_text(Path("missing.pdf"))


def test_empty_pdf(tmp_path):
    """Verify that a PDF without extractable text raises an error."""
    pdf_path = tmp_path / "empty.pdf"

    with pymupdf.open() as document:
        document.new_page()
        document.save(str(pdf_path))

    with pytest.raises(ValueError):
        extract_text(pdf_path)
