import requests
import pymupdf
import os
from dotenv import load_dotenv

load_dotenv()

pdf_path = "raw_data/document_to_anonymize.pdf"
instructions_path = "submission/prompt.txt"

def extract_text_from_pdf(path: str) -> str:
    """
      Extracts text content from all pages of a PDF file.
    """
    text = ""
    with pymupdf.open(path) as doc:
        for page in doc:
            text += page.get_text()
    return text

raw_text = extract_text_from_pdf(pdf_path)
print(raw_text)






