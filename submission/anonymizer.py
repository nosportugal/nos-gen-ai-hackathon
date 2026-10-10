import os
import pymupdf
import requests
from dotenv import load_dotenv

load_dotenv()

pdf_path = "raw_data/document_to_anonymize.pdf"
instructions_path = "submission/prompt.txt"
output_path = "submission/submission.txt"



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

def strip_fences(text: str) -> str:
    """Removes markdown code fences if the model adds them."""
    lines = [ln for ln in text.splitlines()
             if not ln.strip().startswith("```")]
    return "\n".join(lines)


def read_prompt_file(path: str) -> str:
    """Reads the static instructions from a text file."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"The file {path} was not found. Please create it.")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

