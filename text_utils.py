import fitz
import unicodedata
import re

def extract_text_from_pdf(path: str) -> str:
    """
      Extracts text content from all pages of a PDF file.

      Parameters:
          path (str): The file path to the PDF document.

      Returns:
          str: The extracted text from the entire PDF.
    """
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def remove_all_special_characters(text: str) -> str:
    """
    Normalizes and cleans a text string by removing accents, punctuation, and special characters.

    Steps:
        1. Converts accented characters to their ASCII equivalents.
        2. Removes all characters except letters, numbers, and spaces.
        3. Collapses multiple spaces into a single space.

    Parameters:
        text (str): The input string to be cleaned.

    Returns:
        str: The cleaned and normalized string.
    """
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")

    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()

