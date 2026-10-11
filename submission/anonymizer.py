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



def drop_empty_lines(text: str) -> str:
    """The only layout change allowed by the brief: remove empty lines."""
    # 1. Break the text into a list of lines
    raw_lines = text.splitlines()
    
    # 2. Loop through and strip trailing whitespace from each line
    rstripped_lines = []
    for line in raw_lines:
        rstripped_lines.append(line.rstrip())
        
    # 3. Filter out lines that are completely empty or just spaces
    filtered_lines = []
    for line in rstripped_lines:
        if line.strip():
            filtered_lines.append(line)
            
    # 4. Join the valid lines back together with newlines
    return "\n".join(filtered_lines)



def strip_fences(text: str) -> str:
    """Removes markdown code fences if the model adds them."""
    # 1. Break the text into a list of lines
    raw_lines = text.splitlines()
    
    # 2. Loop through and keep lines that don't start with ```
    filtered_lines = []
    for line in raw_lines:
        # Check if the line, ignoring leading spaces, starts with a fence
        if not line.strip().startswith("```"):
            filtered_lines.append(line)
            
    # 3. Join the remaining lines back together
    return "\n".join(filtered_lines)


