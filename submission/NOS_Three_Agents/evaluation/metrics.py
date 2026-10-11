"""Evaluation metrics. Shared evaluation code, not part of any agent.

Unit: one maskable source word (component). Denominators:

    primary components = reference MASK + reference KEEP components
    (reference AMBIGUOUS components are excluded and counted apart)

    TP  reference MASK and hidden in the output
    FN  reference MASK and not hidden (identical or merely altered)
    FP  reference KEEP and hidden
    TN  reference KEEP and not hidden

    precision          TP / (TP + FP)
    recall             TP / (TP + FN)
    f1                 2PR / (P + R)
    exact_agreement    (MASK words carrying the exact policy mask
                        + KEEP words left identical) / primary components
    over_masking_rate  FP / reference KEEP components
    under_masking_rate FN / reference MASK components
    entity_full_mask_rate
                       reference MASK entities whose every word is hidden
                       / reference MASK entities (exact-span boundary:
                       the entity's own words, nothing more or less)

"Hidden" means the output word is the exact policy mask or a
non-conforming mask (asterisks and punctuation only). A word that was
partly masked or altered still counts as not hidden.

A ratio with a zero denominator is None and is reported as N/A. When an
output cannot be aligned without gaps, every accuracy field is None.
All values are PROVISIONAL while the reference is unreviewed.
"""
from __future__ import annotations

import difflib

from shared.textmodel import split_lines

HIDDEN = ("M", "N")


def ratio(num, den):
    return None if not den else num / den


def accuracy(doc, reference: dict, states) -> dict:
    """Word-level accuracy for an output with a gap-free alignment."""
    ref = {row["component_id"]: row for row in reference["components"]}
    state_of = {tok.comp_id: st for tok, st in zip(doc.tokens, states)}
    tp = fp = fn = tn = exact = amb = amb_hidden = 0
    for comp_id, row in ref.items():
        state = state_of[comp_id]
        hidden = state in HIDDEN
        if row["decision"] == "AMBIGUOUS":
            amb += 1
            amb_hidden += hidden
            continue
        if row["decision"] == "MASK":
            tp += hidden
            fn += not hidden
            exact += state == "M"
        else:
            fp += hidden
            tn += not hidden
            exact += state == "I"
    precision, recall = ratio(tp, tp + fp), ratio(tp, tp + fn)
    f1 = None
    if precision is not None and recall is not None:
        f1 = ratio(2 * precision * recall, precision + recall)
    entities = [e for e in reference["entities"] if e["decision"] == "MASK"]
    full = sum(
        all(state_of[c] in HIDDEN for c in e["component_ids"])
        for e in entities
    )
    return {
        "ref_mask_n": tp + fn,
        "ref_keep_n": fp + tn,
        "ref_ambiguous_n_excluded": amb,
        "ambiguous_hidden_n": amb_hidden,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact_agreement": ratio(exact, tp + fp + fn + tn),
        "over_masking_rate": ratio(fp, fp + tn),
        "under_masking_rate": ratio(fn, tp + fn),
        "ref_mask_entities": len(entities),
        "entity_full_mask_rate": ratio(full, len(entities)),
    }


def empty_accuracy() -> dict:
    keys = ("ref_mask_n", "ref_keep_n", "ref_ambiguous_n_excluded",
            "ambiguous_hidden_n", "tp", "fp", "fn", "tn", "precision",
            "recall", "f1", "exact_agreement", "over_masking_rate",
            "under_masking_rate", "ref_mask_entities",
            "entity_full_mask_rate")
    return {key: None for key in keys}


def _canon(text: str) -> str:
    """Final newline is not significant (frozen newline policy)."""
    return "\n".join(split_lines(text))


def fidelity(doc, candidate: str, states) -> dict:
    """Unauthorised character edits against the allowed rendering.

    The allowed rendering is the source with exactly the words the output
    hides replaced by their policy mask. Any character difference between
    it and the candidate is an unauthorised edit.
    """
    if states is None:
        return {"char_inserted": None, "char_deleted": None,
                "char_substituted": None}
    hidden = [t.comp_id for t, st in zip(doc.tokens, states)
              if st in HIDDEN]
    allowed = _canon(doc.render(hidden))
    matcher = difflib.SequenceMatcher(None, allowed, _canon(candidate),
                                      autojunk=False)
    ins = dele = sub = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        a, b = i2 - i1, j2 - j1
        if tag == "insert":
            ins += b
        elif tag == "delete":
            dele += a
        elif tag == "replace":
            sub += min(a, b)
            ins += max(0, b - a)
            dele += max(0, a - b)
    return {"char_inserted": ins, "char_deleted": dele,
            "char_substituted": sub}


def reference_rendering(doc, reference: dict) -> str:
    """The output implied by the reference (AMBIGUOUS left unmasked).

    For evaluation only. It is never given to an agent.
    """
    ids = [r["component_id"] for r in reference["components"]
           if r["decision"] == "MASK"]
    return doc.render(ids)


def reference_agreement(doc, reference: dict, candidate: str) -> dict:
    want = split_lines(reference_rendering(doc, reference))
    got = split_lines(candidate)
    same = sum(1 for a, b in zip(want, got) if a == b)
    return {
        "exact_reference_match": want == got,
        "lines_equal_reference": same,
        "reference_lines": len(want),
    }


def disagreement(state_lists) -> dict:
    """Pairwise differences in hidden/not-hidden across repeated runs."""
    pairs = []
    for i in range(len(state_lists)):
        for j in range(i + 1, len(state_lists)):
            a, b = state_lists[i], state_lists[j]
            pairs.append(sum(
                (x in HIDDEN) != (y in HIDDEN) for x, y in zip(a, b)
            ))
    if not pairs:
        return {"pairs_compared": 0, "max_words_differing": None,
                "mean_words_differing": None}
    return {"pairs_compared": len(pairs),
            "max_words_differing": max(pairs),
            "mean_words_differing": sum(pairs) / len(pairs)}
