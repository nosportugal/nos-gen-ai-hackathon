"""Agent A - Gated Rewrite.

One Gemini call returns the whole transformed document. Python validates
the response and saves it byte-for-byte; it never modifies it.
"""
from __future__ import annotations

from pathlib import Path

from shared import config
from shared.gemini_client import GenRequest, InputTooLarge, check_input_size
from shared.policy import fill
from shared.runner import (
    FAILED,
    INVALID,
    VALID,
    Run,
    file_hashes,
    load_agent_files,
)
from shared.validation import summarize, validate_candidate

HERE = Path(__file__).resolve().parent
FILES = ("system_prompt.txt", "user_template.txt", "config.json")


def document_block(doc) -> str:
    """The source exactly as stored, ending with one newline."""
    return doc.text if doc.text.endswith("\n") else doc.text + "\n"


def build_request(ctx) -> GenRequest:
    files = load_agent_files(HERE, FILES[:2])
    system = fill(
        files["system_prompt.txt"],
        POLICY_BLOCK=ctx.policy.prompt_block(),
        WORD_RULE=ctx.policy.word_rule_text(),
    )
    user = fill(files["user_template.txt"], DOCUMENT=document_block(ctx.doc))
    return GenRequest("A.rewrite", system, user)


def run(ctx, trial: int = 1) -> dict:
    cfg = config.load_json(HERE / "config.json")
    run_ = Run(ctx, "A", cfg["agent_name"], HERE.name, trial, cfg,
               file_hashes(HERE, FILES))
    request = build_request(ctx)
    run_.save_request("request", "stage1_request.json", request)
    try:
        size = check_input_size(
            ctx.model_cfg,
            len(request.system_instruction) + len(request.user_text),
            len(ctx.doc.text),
        )
    except InputTooLarge as exc:
        return run_.finish(FAILED, f"INPUT_TOO_LARGE: {exc}", {})

    resp = run_.call("stage1_rewrite", request)
    if resp.text is None:
        return run_.finish(
            FAILED, f"{resp.status}: {resp.error}", {"input_size": size}
        )
    # Exact returned text, saved even when the run is a failure.
    run_.save("candidate", "candidate.txt", resp.text)
    with run_.timed("validation_s"):
        validation = validate_candidate(ctx.doc, resp.text, ctx.policy)
    run_.save("validation", "validation.json", validation)
    summary = summarize(validation)
    summary["input_size"] = size
    if not resp.ok:
        return run_.finish(FAILED, f"{resp.status}: {resp.error}", summary)
    if validation["structural_pass"]:
        return run_.finish(VALID, None, summary)
    return run_.finish(
        INVALID,
        "STRUCTURAL_VALIDATION_FAILED: "
        + str(validation["strict"]["violation_counts"]),
        summary,
    )
