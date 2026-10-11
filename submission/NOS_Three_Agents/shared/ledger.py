"""Mechanical validation of decision ledgers (agent B) and spans (agent C).

An entry names one run of consecutive words on one retained line:

    {"line": 5, "first_token": 2, "last_token": 5,
     "quote": "Maria Conceição Oliveira Santos",
     "decision": "MASK", "category": "PERSON_NAME", "reason": "..."}

IDs are generated locally (line number, word position). Python maps them
to source offsets; the model never supplies character offsets. The quote
must equal the source text of the run exactly, in one of two forms: from
the first word's core to the last word's core, or from the first word's
first character to the last word's last character. Nothing is matched by
similarity and nothing is replaced globally.

Frozen handling (shared by B and C):
- exact duplicate entries: collapsed, reported as a warning;
- overlapping entries with the same decision: merged, warning;
- overlapping entries with different decisions: error;
- adjacent entries: independent, no effect on rendering;
- any error blocks rendering; entries are never silently discarded;
- AMBIGUOUS entries are valid, recorded, and rendered as KEEP.
"""
from __future__ import annotations

import json

from . import schema

MAX_REASON_CHARS = 300


def parse_ledger(text: str, ledger_schema: dict, key: str):
    """Parse and schema-check model JSON. Returns (entries, error).

    The text is parsed as returned: no fence stripping, no repair.
    """
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"JSON_INVALID: {exc.msg} at char {exc.pos}"
    errors = schema.validate(parsed, ledger_schema)
    if errors:
        return None, "SCHEMA_INVALID: " + "; ".join(errors[:5])
    return parsed[key], None


def validate_entries(doc, entries, policy, allowed_decisions) -> dict:
    errors, warnings, resolved = [], [], []
    owner = {}  # comp_id -> (decision, entry index)
    seen = {}

    def err(k, code, detail):
        errors.append({"entry": k, "code": code, "detail": detail})

    for k, entry in enumerate(entries):
        line = entry.get("line")
        first = entry.get("first_token")
        last = entry.get("last_token")
        decision = entry.get("decision")
        category = entry.get("category")
        quote = entry.get("quote", "")
        if decision not in allowed_decisions:
            err(k, "decision_not_allowed", str(decision))
            continue
        if policy.decision_of(category) != decision:
            err(
                k,
                "category_contradicts_decision",
                f"{category} is not a {decision} category",
            )
            continue
        if len(entry.get("reason", "")) > MAX_REASON_CHARS:
            err(k, "reason_too_long", f"> {MAX_REASON_CHARS} characters")
            continue
        t_first = doc.get(line, first) if _ints(line, first) else None
        t_last = doc.get(line, last) if _ints(line, last) else None
        if t_first is None or t_last is None:
            err(k, "invalid_location", f"L{line} T{first}-T{last}")
            continue
        if first > last:
            err(k, "reversed_range", f"T{first} > T{last}")
            continue
        if quote not in doc.run_quotes(t_first, t_last):
            err(
                k,
                "quote_mismatch",
                f"L{line} T{first}-T{last}: quote {quote[:50]!r} is not "
                "the source text at that location",
            )
            continue
        toks = doc.line_tokens[line][first - 1:last]
        comps = [t for t in toks if t.maskable]
        if not comps:
            err(k, "no_maskable_word", f"L{line} T{first}-T{last}")
            continue
        key = (line, first, last, decision)
        if key in seen:
            warnings.append(
                {
                    "entry": k,
                    "code": "duplicate_collapsed",
                    "detail": f"same as entry {seen[key]}",
                }
            )
            continue
        seen[key] = k
        clash = False
        for tok in comps:
            prior = owner.get(tok.comp_id)
            if prior and prior[0] != decision:
                err(
                    k,
                    "contradictory_overlap",
                    f"{tok.comp_id} is {prior[0]} in entry {prior[1]} "
                    f"and {decision} here",
                )
                clash = True
                break
        if clash:
            continue
        merged = [t.comp_id for t in comps if t.comp_id in owner]
        if merged:
            warnings.append(
                {
                    "entry": k,
                    "code": "overlap_same_decision_merged",
                    "detail": ", ".join(merged[:6]),
                }
            )
        for tok in comps:
            owner.setdefault(tok.comp_id, (decision, k))
        resolved.append(
            {
                "entry": k,
                "decision": decision,
                "category": category,
                "line": line,
                "first_token": first,
                "last_token": last,
                "quote": quote,
                "reason": entry.get("reason", ""),
                "start": comps[0].core_start,
                "end": comps[-1].core_end,
                "components": [
                    {
                        "id": t.comp_id,
                        "start": t.core_start,
                        "end": t.core_end,
                        "text": t.core,
                    }
                    for t in comps
                ],
            }
        )

    by_decision = {d: [] for d in ("MASK", "AMBIGUOUS", "KEEP")}
    for comp_id, (decision, _) in owner.items():
        by_decision[decision].append(comp_id)
    for ids in by_decision.values():
        ids.sort()
    ok = not errors
    return {
        "ok": ok,
        "entries_received": len(entries),
        "entries_resolved": len(resolved),
        "errors": errors,
        "warnings": warnings,
        "resolved": resolved,
        "mask_ids": by_decision["MASK"] if ok else [],
        "ambiguous_ids": by_decision["AMBIGUOUS"] if ok else [],
        "keep_ids": by_decision["KEEP"] if ok else [],
        "approval": "mechanically validated against the frozen policy; "
        "no human review" if ok else "NOT VALID - rendering blocked",
    }


def _ints(*values) -> bool:
    return all(
        isinstance(v, int) and not isinstance(v, bool) for v in values
    )


def render_ids(validated: dict, policy) -> list:
    """Component ids to mask after applying the frozen ambiguity rule."""
    if not validated["ok"]:
        raise ValueError("ledger is not valid; rendering is blocked")
    ids = list(validated["mask_ids"])
    if policy.render_ambiguous_as == "MASK":
        ids += validated["ambiguous_ids"]
    return sorted(set(ids))


def ledger_agreement(doc, states, expected_mask_ids) -> dict:
    """Compare what an output actually masks with what a ledger approved."""
    if states is None:
        return {"evaluable": False, "pass": False}
    expected = set(expected_mask_ids)
    actual = {
        tok.comp_id
        for tok, st in zip(doc.tokens, states)
        if st in ("M", "N")
    }
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    return {
        "evaluable": True,
        "pass": not missing and not extra,
        "approved_mask_words": len(expected),
        "masked_words_in_output": len(actual),
        "approved_but_not_masked": missing[:40],
        "masked_but_not_approved": extra[:40],
    }
