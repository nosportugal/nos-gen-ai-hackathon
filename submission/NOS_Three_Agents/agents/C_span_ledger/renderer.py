"""Deterministic rendering for agent C.

Spans are resolved to source offsets through local line and word IDs and
verified against the source text. Any invalid span blocks rendering: there
is no fuzzy matching, no global replacement and no partial output.

Frozen handling of special cases (same rules as agent B's ledger):
- adjacent spans: independent; adjacency has no effect because every
  word is masked on its own;
- exact duplicates: collapsed with a warning;
- overlapping spans with the same decision: merged with a warning;
- overlapping spans with different decisions: validation error;
- AMBIGUOUS spans: valid, recorded, rendered unmasked.
"""
from __future__ import annotations

from shared.ledger import render_ids, validate_entries

SPAN_DECISIONS = ("MASK", "AMBIGUOUS")


def resolve_spans(doc, spans, policy) -> dict:
    """Map spans to verified source offsets. Never guesses."""
    return validate_entries(doc, spans, policy, SPAN_DECISIONS)


def render(doc, resolved: dict, policy) -> dict:
    """Render validated spans; raises if the spans are not valid."""
    mask_ids = render_ids(resolved, policy)
    text = doc.render(mask_ids)
    replacements = [
        {
            "id": comp_id,
            "start": doc.token(comp_id).core_start,
            "end": doc.token(comp_id).core_end,
            "source_text": doc.token(comp_id).core,
            "replacement": "*",
        }
        for comp_id in mask_ids
    ]
    return {
        "text": text,
        "mask_ids": mask_ids,
        "replacements": replacements,
        "ambiguous_left_unmasked": resolved["ambiguous_ids"],
    }
