import os
import pymupdf
import requests
from dotenv import load_dotenv

load_dotenv()

pdf_path = "raw_data/document_to_anonymize.pdf"
instructions_path = "submission/prompt.txt"
output_path = "submission/submission.txt"

MODEL = "gemini-3.8-flash"  # change here if Google retires it again
API_KEY = os.getenv("API_KEY")
API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{MODEL}:generateContent?key={API_KEY}"
)


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
1    lines = (line.rstrip() for line in text.splitlines())
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


def generate_content(prompt_text: str, temperature: float) -> dict:
    """Generates content based on the given prompt text and temperature.

    Args:
        prompt_text (str): The text prompt to generate content from.
        temperature (float): The temperature parameter for controlling
            randomness.
    """
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": temperature},
    }
    response = requests.post(
    API_URL, headers=headers, json=body)
    return response.json()


def get_response_text(output: dict) -> str:
    """Pulls the text out of Gemini's reply, or shows the API error."""
    if "candidates" not in output:
        raise RuntimeError(f"API Error Details: {output}")
    return output["candidates"][0]["content"]["parts"][0]["text"]

