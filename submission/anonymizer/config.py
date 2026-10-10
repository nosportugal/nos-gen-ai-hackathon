import os
from pathlib import Path

from dotenv import load_dotenv

SUBMISSION_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = SUBMISSION_DIR.parent

PROMPT_PATH = SUBMISSION_DIR / "prompt.txt"
SUBMISSION_PATH = SUBMISSION_DIR / "submission.txt"
OUTPUTS_DIR = SUBMISSION_DIR / "outputs"
PDF_PATH = REPO_DIR / "raw_data" / "document_to_anonymize.pdf"

TEMPERATURE = 0.0
RETRY_CODES = {429, 500, 503}
MAX_RETRIES = 3


def api_key() -> str:
    load_dotenv(REPO_DIR / ".env")
    key = os.getenv("API_KEY")
    if not key:
        raise RuntimeError("API_KEY environment variable is not set")
    return key


def pipeline_model() -> str:
    return os.getenv("MODEL", "gemini-2.5-flash")
