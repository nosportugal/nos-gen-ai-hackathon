"""The prompt: instructions from a file, the document as the user message."""
from pathlib import Path

from . import SUBMISSION

DEFAULT_PROMPT = SUBMISSION / "prompt.txt"
EXAMPLES = SUBMISSION / "prompts"


def load_prompt(path: Path = DEFAULT_PROMPT) -> str:
    text = Path(path).read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(
            f"{path} is empty; pass --prompt or copy one from {EXAMPLES}")
    return text


def build_messages(system: str, document: str) -> tuple:
    """Return (system instruction, user message).

    The document is sent as data between tags, never inside the
    instructions. Tags do not prevent prompt injection by themselves.
    """
    if not document.endswith("\n"):
        document += "\n"
    return system, f"<document>\n{document}</document>\n"
