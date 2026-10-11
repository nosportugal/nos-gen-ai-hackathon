"""Anonymization agent.

    PDF -> raw_uncensored_document.txt -> prompt -> LLM -> answer file

One model call returns the whole document with personal data masked.
The answer is written exactly as returned. The agent does not check or
score it: use benchmark/ for that.

Usage (from submission/):
    python -m agent                          # Gemini, writes submission.txt
    python -m agent --provider local         # llama.cpp on localhost:8080
    python -m agent --prompt prompts/prompt_v3_2.txt
    python -m agent --pdf input.pdf --out answer.txt
    python -m agent --dry-run                # show the prompt, no call

Exit code: 0 answer written, 1 model failure, 2 not run.
"""
import argparse
import os
import sys
from pathlib import Path

from langchain_core.runnables import RunnablePassthrough

from . import SUBMISSION
from .extraction import DEFAULT_PDF, extract_pdf
from .llm import (
    DEFAULT_LOCAL_URL,
    DEFAULT_MODELS,
    TIMEOUT_S,
    answer_text,
    api_key,
    get_llm,
    to_messages,
)
from .prompt import DEFAULT_PROMPT, build_messages, load_prompt

DEFAULT_OUT = SUBMISSION / "submission.txt"

# Each step adds one key to the state dict and passes the rest along.
prepare = (
    RunnablePassthrough.assign(document=lambda s: extract_pdf(s["pdf"]))
    | RunnablePassthrough.assign(
        messages=lambda s: build_messages(s["system"], s["document"]))
)
answer = (
    RunnablePassthrough.assign(
        reply=lambda s: s["llm"].invoke(to_messages(*s["messages"])))
    | RunnablePassthrough.assign(output=lambda s: answer_text(s["reply"]))
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", choices=DEFAULT_MODELS,
                        default=os.environ.get("LLM_PROVIDER", "gemini"))
    parser.add_argument("--model", help="model name (default per provider)")
    parser.add_argument("--base-url", default=DEFAULT_LOCAL_URL,
                        help="URL of the local OpenAI-compatible server")
    parser.add_argument("--timeout", type=float, default=TIMEOUT_S,
                        help=f"seconds per model call (default {TIMEOUT_S})")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT,
                        help="instructions file (default: submission/"
                        "prompt.txt)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="answer file (default: submission/"
                        "submission.txt)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    model = args.model or DEFAULT_MODELS[args.provider]

    try:
        system = load_prompt(args.prompt)
    except ValueError as exc:
        print(exc)
        return 2
    state = prepare.invoke({"pdf": args.pdf, "system": system})
    system, user = state["messages"]
    if args.dry_run:
        print(system + "\n" + user[:200] + "...")
        print(f"\n{args.provider}:{model}, "
              f"{len(system) + len(user)} prompt chars")
        return 0

    try:
        llm = get_llm(args.provider, model, args.base_url,
                      args.timeout)
    except ValueError as exc:
        print(exc)
        return 2
    print(f"running {args.provider}:{model}", file=sys.stderr)
    try:
        state = answer.invoke({**state, "llm": llm})
    except Exception as exc:  # API, network or incomplete answer
        error = f"{type(exc).__name__}: {exc}"
        key = api_key()
        print("FAILED: " + (error.replace(key, "[KEY]") if key else error))
        return 1

    args.out.write_bytes(state["output"].encode("utf-8"))
    print(f"wrote {args.out}")
    if (args.out.resolve() == DEFAULT_OUT
            and args.prompt.resolve() != DEFAULT_PROMPT):
        # prompt.txt must hold the prompt that produced submission.txt.
        DEFAULT_PROMPT.write_bytes(system.encode("utf-8"))
        print(f"wrote {DEFAULT_PROMPT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
