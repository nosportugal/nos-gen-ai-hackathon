import pymupdf

from anonymizer.pdf_reconstructor import reconstruct_pdf
from anonymizer.spans import Category, Span


def test_reconstruct_pdf_removes_sensitive_text():
    """Sensitive text disappears; unrelated text remains."""

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Nome: Ana Correia")
        page.insert_text((72, 100), "Departamento: Informatica")
        original_pdf = document.tobytes()

    spans = [
        Span(
            line=1,
            text="Ana Correia",
            category=Category.NAME,
        )
    ]

    result_pdf = reconstruct_pdf(original_pdf, spans)

    with pymupdf.open(
        stream=result_pdf,
        filetype="pdf",
    ) as document:
        result_text = document[0].get_text()

        assert "Ana" not in result_text
        assert "Correia" not in result_text
        assert result_text.count("*") == 2
        assert "Departamento: Informatica" in result_text


def test_reconstruct_pdf_preserves_unmarked_words():
    """Keep identical words that were not marked as sensitive."""

    with pymupdf.open() as document:
        page1 = document.new_page()
        page1.insert_text((72, 72), "Nome: Ana Correia")

        page2 = document.new_page()
        page2.insert_text((72, 72), "Nota: Ana confirmou a visita")

        original_pdf = document.tobytes()

    spans = [
        Span(
            line=1,
            text="Ana Correia",
            category=Category.NAME,
        )
    ]

    result_pdf = reconstruct_pdf(original_pdf, spans)

    with pymupdf.open(
        stream=result_pdf,
        filetype="pdf",
    ) as document:
        first_page = document[0].get_text()
        second_page = document[1].get_text()

        assert "Ana Correia" not in first_page
        assert first_page.count("*") == 2
        assert "Nota: Ana confirmou a visita" in second_page
