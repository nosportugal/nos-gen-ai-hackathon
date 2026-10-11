"""Chat models: Gemini, or a local OpenAI-compatible server.

A local server is for example llama.cpp started with:
    llama-server -m model.gguf --port 8080
"""
import os

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from . import SUBMISSION

DEFAULT_MODELS = {"gemini": "gemini-3.6-flash", "local": "local"}
DEFAULT_LOCAL_URL = os.environ.get("LOCAL_LLM_URL", "http://localhost:8080/v1")
MAX_OUTPUT_TOKENS = 16384
TIMEOUT_S = 300
ATTEMPTS = 1  # no retry: a failed call usually fails again
KEY_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def api_key():
    """Gemini key from the environment, else from submission/.env."""
    for name in KEY_NAMES:
        if os.environ.get(name, "").strip():
            return os.environ[name].strip()
    env = SUBMISSION / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            value = value.strip().strip("\"'")
            if name.strip() in KEY_NAMES and value:
                return value
    return None


def get_llm(provider: str, model: str = None,
            base_url: str = DEFAULT_LOCAL_URL,
            timeout: float = TIMEOUT_S) -> BaseChatModel:
    """Gemini uses temperature 0.0; local models use their own default."""
    model = model or DEFAULT_MODELS[provider]
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        key = api_key()
        if not key:
            raise ValueError(
                "no GEMINI_API_KEY in the environment or submission/.env")
        return ChatGoogleGenerativeAI(
            model=model, google_api_key=key, temperature=0.0,
            max_output_tokens=MAX_OUTPUT_TOKENS, timeout=timeout,
            max_retries=ATTEMPTS,  # Google SDK: total attempts
        )
    if provider == "local":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model, base_url=base_url, api_key="none",
            max_tokens=MAX_OUTPUT_TOKENS, timeout=timeout,
            max_retries=ATTEMPTS - 1,  # OpenAI client: retries after the first
        )
    raise ValueError(f"unknown provider: {provider}")


def to_messages(system: str, user: str) -> list:
    return [SystemMessage(system), HumanMessage(user)]


def answer_text(message) -> str:
    """The answer text; raises if the model did not finish normally."""
    finish = message.response_metadata.get("finish_reason")
    if str(finish).upper() != "STOP":  # Gemini "STOP", OpenAI "stop"
        raise RuntimeError(f"finish_reason={finish} (answer not complete)")
    text = message.text  # text blocks only, no thinking
    # langchain-core < 1.0 (Python 3.9) has text() as a method.
    return text if isinstance(text, str) else text()
