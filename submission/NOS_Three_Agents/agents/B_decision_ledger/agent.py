"""Agent B - Decision Ledger + LLM Rendering.

Stage 1 (one Gemini call) returns a schema-validated ledger of
MASK / AMBIGUOUS / KEEP decisions anchored to local line and word IDs.
Python validates every entry. Stage 2 (a second Gemini call) receives the
source and the validated decisions and returns the transformed document.
Python checks that response and never modifies it.

If stage 1 fails in any way, stage 2 is not called.
"""
from __future__ import annotations

import json
from pathlib import Path

from shared import config
from shared.gemini_client import GenRequest, InputTooLarge, check_input_size
from shared.ledger import (
    ledger_agreement,
    parse_ledger,
    render_ids,
    validate_entries,
)
from shared.policy import fill
from shared.runner import (
    FAILED,
    INVALID,
    VALID,
    Run,
    file_hashes,
    load_agent_files,
)
from shared.textmodel import split_lines
from shared.validation import summarize, validate_candidate

HERE = Path(__file__).resolve().parent
PROMPTS = (
    "stage1_system_prompt.txt",
    "stage1_user_template.txt",
    "stage2_system_prompt.txt",
    "stage2_user_template.txt",
)
FILES = PROMPTS + ("ledger_schema.json", "config.json")
DECISIONS = ("MASK", "AMBIGUOUS", "KEEP")


def document_block(doc) -> str:
    return doc.text if doc.text.endswith("\n") else doc.text + "\n"


def stage1_request(ctx, files, ledger_schema) -> GenRequest:
    system = fill(
        files["stage1_system_prompt.txt"],
        POLICY_BLOCK=ctx.policy.prompt_block(),
    )
    user = fill(
        files["stage1_user_template.txt"],
        TOKEN_INDEX=ctx.doc.token_index_view(),
    )
    return GenRequest("B.ledger", system, user, ledger_schema)


def decision_lines(doc, validated: dict, mask_ids) -> str:
    """One line per decided word, in document order."""
    mask_ids = set(mask_ids)
    decided = (
        validated["mask_ids"]
        + validated["ambiguous_ids"]
        + validated["keep_ids"]
    )
    rows = []
    for comp_id in sorted(set(decided)):
        tok = doc.token(comp_id)
        action = "MASK" if comp_id in mask_ids else "KEEP"
        word = json.dumps(tok.core, ensure_ascii=False)
        rows.append(f"{action} L{tok.line:03d} T{tok.index} {word}")
    return "\n".join(rows)


def stage2_request(ctx, files, validated, mask_ids) -> GenRequest:
    system = fill(
        files["stage2_system_prompt.txt"],
        WORD_RULE=ctx.policy.word_rule_text(),
    )
    user = fill(
        files["stage2_user_template.txt"],
        DOCUMENT=document_block(ctx.doc),
        TOKEN_INDEX=ctx.doc.token_index_view(),
        DECISIONS=decision_lines(ctx.doc, validated, mask_ids),
    )
    return GenRequest(
        "B.render", system, user, mock_hint={"mask_ids": list(mask_ids)}
    )


def run(ctx, trial: int = 1) -> dict:
    cfg = config.load_json(HERE / "config.json")
    run_ = Run(ctx, "B", cfg["agent_name"], HERE.name, trial, cfg,
               file_hashes(HERE, FILES))
    files = load_agent_files(HERE, PROMPTS)
    ledger_schema = config.load_json(HERE / "ledger_schema.json")
    not_called = {"stage2": "NOT_CALLED"}

    # ---- stage 1: decisions -------------------------------------------
    req1 = stage1_request(ctx, files, ledger_schema)
    run_.save_request("stage1_request", "stage1_request.json", req1)
    try:
        check_input_size(
            ctx.model_cfg, len(req1.system_instruction) + len(req1.user_text)
        )
    except InputTooLarge as exc:
        return run_.finish(FAILED, f"INPUT_TOO_LARGE: {exc}", not_called)
    resp1 = run_.call("stage1_ledger", req1)
    if not resp1.ok:
        return run_.finish(
            FAILED, f"STAGE1_{resp1.status}: {resp1.error}", not_called
        )
    entries, error = parse_ledger(resp1.text, ledger_schema, "entries")
    if error:
        return run_.finish(FAILED, "STAGE1_" + error, not_called)
    run_.save("stage1_ledger", "stage1_ledger.json", {"entries": entries})
    with run_.timed("validation_s"):
        validated = validate_entries(ctx.doc, entries, ctx.policy, DECISIONS)
    run_.save("stage1_ledger_validation",
              "stage1_ledger_validation.json", validated)
    ledger_summary = {
        "ledger_valid": validated["ok"],
        "ledger_entries": validated["entries_received"],
        "ledger_errors": len(validated["errors"]),
        "ledger_warnings": len(validated["warnings"]),
        "ledger_first_errors": validated["errors"][:3],
        "decision_approval": cfg["decision_approval"],
    }
    if not validated["ok"]:
        return run_.finish(
            FAILED,
            f"STAGE1_LEDGER_INVALID: {len(validated['errors'])} error(s)",
            {**ledger_summary, **not_called},
        )
    mask_ids = render_ids(validated, ctx.policy)

    # ---- stage 2: rendering by the model ------------------------------
    req2 = stage2_request(ctx, files, validated, mask_ids)
    run_.save_request("stage2_request", "stage2_request.json", req2)
    try:
        check_input_size(
            ctx.model_cfg,
            len(req2.system_instruction) + len(req2.user_text),
            len(ctx.doc.text),
        )
    except InputTooLarge as exc:
        return run_.finish(
            FAILED, f"INPUT_TOO_LARGE: {exc}", ledger_summary
        )
    resp2 = run_.call("stage2_render", req2)
    if resp2.text is None:
        return run_.finish(
            FAILED, f"STAGE2_{resp2.status}: {resp2.error}", ledger_summary
        )
    # Exact returned text; never replaced by the internal rendering.
    run_.save("candidate", "candidate.txt", resp2.text)
    with run_.timed("validation_s"):
        validation = validate_candidate(ctx.doc, resp2.text, ctx.policy)
        states = validation["alignment_states"]
        agreement = ledger_agreement(
            ctx.doc, list(states) if states else None, mask_ids
        )
        internal = ctx.doc.render(mask_ids)
        validation["ledger_agreement"] = agreement
        validation["equals_internal_reference_rendering"] = split_lines(
            resp2.text
        ) == split_lines(internal)
    run_.save("validation", "validation.json", validation)
    summary = {**summarize(validation), **ledger_summary}
    summary["ledger_agreement_pass"] = agreement["pass"]
    summary["equals_internal_reference_rendering"] = validation[
        "equals_internal_reference_rendering"
    ]
    if not resp2.ok:
        return run_.finish(
            FAILED, f"STAGE2_{resp2.status}: {resp2.error}", summary
        )
    if validation["structural_pass"] and agreement["pass"]:
        return run_.finish(VALID, None, summary)
    reason = []
    if not validation["structural_pass"]:
        reason.append(
            "STRUCTURAL_VALIDATION_FAILED: "
            + str(validation["strict"]["violation_counts"])
        )
    if not agreement["pass"]:
        reason.append("LEDGER_AGREEMENT_FAILED")
    return run_.finish(INVALID, "; ".join(reason), summary)
