import os
from pathlib import Path

from dotenv import load_dotenv

SUBMISSION_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = SUBMISSION_DIR.parent

PROMPT_PATH = SUBMISSION_DIR / "prompt.txt"
SUBMISSION_PATH = SUBMISSION_DIR / "submission.txt"
OUTPUTS_DIR = SUBMISSION_DIR / "outputs"
PDF_PATH = REPO_DIR / "raw_data" / "document_to_anonymize.pdf"

DEFAULT_MODEL = "gemini-3.8-flash"
TEMPERATURE = 0.0
RETRY_CODES = {429, 500, 503}
MAX_RETRIES = 3

# Every setting loads .env itself, so callers may read a model name before
# anything else touched the environment. load_dotenv never overrides
# variables already set in the shell.


def api_key() -> str:
    _load_env()
    key = os.getenv("API_KEY")
    if not key:
        raise RuntimeError("API_KEY environment variable is not set")
    return key


def main_model() -> str:
    _load_env()
    return os.getenv("MAIN_MODEL", DEFAULT_MODEL)


def data_gen_model() -> str:
    _load_env()
    return os.getenv("DATA_GEN_MODEL") or main_model()


def validation_model() -> str | None:
    """The judge model; None means the meaning score is skipped."""
    _load_env()
    return os.getenv("VALIDATION_MODEL")


def _load_env() -> None:
    load_dotenv(REPO_DIR / ".env")
