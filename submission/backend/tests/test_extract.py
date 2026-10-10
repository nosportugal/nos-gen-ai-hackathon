import pymupdf
import pytest

from anonymizer.extract import extract_text, extract_text_from_bytes


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


def test_missing_pdf(tmp_path):
    """Verify that a missing file raises an error."""
    pdf_path = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError):
        extract_text(pdf_path)


def test_empty_pdf(tmp_path):
    """Verify that a PDF without extractable text raises an error."""
    pdf_path = tmp_path / "empty.pdf"

    with pymupdf.open() as document:
        document.new_page()
        document.save(str(pdf_path))

    with pytest.raises(ValueError):
        extract_text(pdf_path)


def test_extract_text_with_string_path(tmp_path):
    """Verify that the function accepts a string path."""
    pdf_path = tmp_path / "test_string.pdf"

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Nome: Maria Santos")
        document.save(str(pdf_path))

    result = extract_text(str(pdf_path))

    assert "Nome: Maria Santos" in result


def test_extract_text_from_bytes():
    """Verify that PDF bytes can be processed directly."""
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Nome: Ana Correia")
        pdf_bytes = document.tobytes()

    result = extract_text_from_bytes(pdf_bytes)

    assert "Nome: Ana Correia" in result
