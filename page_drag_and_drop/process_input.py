# process_input.py



    

def process_text(text):
    # Replace with your own logic
    return text[::-1]


# Define a function to extract all text from a PDF file. It reads every page and returns the combined text.

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

#Defines a function to extract all the special characters in the text, in order to have a raw version of the text

import unicodedata
import re

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
def process_pdf(pdf_path):
    raw_text = extract_text_from_pdf(pdf_path)

    raw_text_cleaned = remove_all_special_characters(raw_text)

    txt_path = pdf_path.replace(".pdf", ".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(raw_text_cleaned)

    print(f"✅ Text extracted and saved to: {txt_path}")

    print("\n--- Preview of Extracted Text ---\n")
    print(raw_text_cleaned)

    return text or "No text found in PDF."