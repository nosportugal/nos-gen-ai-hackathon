import pymupdf


pdf_path = "raw_data/document_to_anonymize.pdf"



def extract_text_from_pdf(path: str) -> str:
    """
    Extracts text content from all pages of a PDF file.
    """
    text = ""
    with pymupdf.open(path) as doc:
        for page in doc:
            text += page.get_text()
    return text


def drop_empty_lines(text: str) -> str:
    """The only layout change allowed by the brief: remove empty lines."""
    lines = (line.rstrip() for line in text.splitlines())
    return "\n".join(line for line in lines if line.strip())

