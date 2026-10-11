"""Agent C - Span Ledger + Deterministic Python Rendering.

One Gemini call returns schema-validated spans anchored to local line and
word IDs with exact quotes. Python verifies every span against the source
and renders the document itself. Invalid spans fail the run; nothing is
rendered from a partly valid span list.
"""
from __future__ import annotations

from pathlib import Path

from shared import config
from shared.gemini_client import GenRequest, InputTooLarge, check_input_size
from shared.ledger import parse_ledger
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

from . import renderer

HERE = Path(__file__).resolve().parent
PROMPTS = ("system_prompt.txt", "user_template.txt")
FILES = PROMPTS + ("span_schema.json", "config.json")


def build_request(ctx, files, span_schema) -> GenRequest:
    system = fill(
        files["system_prompt.txt"], POLICY_BLOCK=ctx.policy.prompt_block()
    )
    user = fill(
        files["user_template.txt"], TOKEN_INDEX=ctx.doc.token_index_view()
    )
    return GenRequest("C.spans", system, user, span_schema)


def run(ctx, trial: int = 1) -> dict:
    cfg = config.load_json(HERE / "config.json")
    run_ = Run(ctx, "C", cfg["agent_name"], HERE.name, trial, cfg,
               file_hashes(HERE, FILES + ("renderer.py",)))
    files = load_agent_files(HERE, PROMPTS)
    span_schema = config.load_json(HERE / "span_schema.json")
    request = build_request(ctx, files, span_schema)
    run_.save_request("request", "stage1_request.json", request)
    try:
        check_input_size(
            ctx.model_cfg,
            len(request.system_instruction) + len(request.user_text),
        )
    except InputTooLarge as exc:
        return run_.finish(FAILED, f"INPUT_TOO_LARGE: {exc}", {})

    resp = run_.call("stage1_spans", request)
    if not resp.ok:
        return run_.finish(FAILED, f"{resp.status}: {resp.error}", {})
    spans, error = parse_ledger(resp.text, span_schema, "spans")
    if error:
        return run_.finish(FAILED, "SPANS_" + error, {})
    run_.save("spans", "stage1_spans.json", {"spans": spans})

    with run_.timed("validation_s"):
        resolved = renderer.resolve_spans(ctx.doc, spans, ctx.policy)
    run_.save("resolved_spans", "resolved_spans.json", resolved)
    span_summary = {
        "spans_valid": resolved["ok"],
        "spans_received": resolved["entries_received"],
        "span_errors": len(resolved["errors"]),
        "span_warnings": len(resolved["warnings"]),
        "span_first_errors": resolved["errors"][:3],
    }
    if not resolved["ok"]:
        # No rendering from an invalid span list, not even a partial one.
        return run_.finish(
            FAILED,
            f"SPANS_INVALID: {len(resolved['errors'])} error(s)",
            span_summary,
        )

    with run_.timed("render_s"):
        rendered = renderer.render(ctx.doc, resolved, ctx.policy)
    run_.save("source_map", "source_map.json", {
        "source_sha256": ctx.source_sha256,
        "line_map": ctx.doc.source_map(),
        "replacements": rendered["replacements"],
        "ambiguous_left_unmasked": rendered["ambiguous_left_unmasked"],
    })
    run_.save("candidate", "candidate.txt", rendered["text"])
    with run_.timed("validation_s"):
        validation = validate_candidate(
            ctx.doc, rendered["text"], ctx.policy
        )
    run_.save("validation", "validation.json", validation)
    summary = {**summarize(validation), **span_summary}
    summary["candidate_written_by"] = "Python renderer (not the model)"
    if validation["structural_pass"]:
        return run_.finish(VALID, None, summary)
    return run_.finish(
        INVALID,
        "RENDERED_OUTPUT_FAILED_VALIDATION: "
        + str(validation["strict"]["violation_counts"]),
        summary,
    )
