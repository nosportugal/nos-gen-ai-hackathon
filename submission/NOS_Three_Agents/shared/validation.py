"""Candidate validation for model-written documents (agents A and B).

Two independent checks are provided.

1. ``strict_check``: line-by-line structural validity. An output line is
   valid only if it equals its source line with some whole words replaced
   by their exact masked form; whitespace must match exactly.

2. ``align``: a monotonic source/output word alignment restricted to the
   allowed transformations (identical word, exact mask, non-conforming
   mask). It uses no fuzzy text similarity. If more than one optimal
   alignment exists the result is UNALIGNABLE and no positions are
   reported.

Neither check says anything about whether the right words were masked.
"""
from __future__ import annotations

from collections import Counter

from .textmodel import MASK, TOKEN_RE, is_blank, split_lines

MAX_REPORTED = 60
INF = 10 ** 9
COUNT_CAP = 10 ** 6

# Per-word states
IDENTICAL = "I"  # output word equals the source word
MASK_EXACT = "M"  # output word is the policy masked form
MASK_NONCONFORMING = "N"  # hidden, but not the exact masked form
ALTERED = "A"  # any other change (still readable or partly readable)
DELETED = "D"  # source word has no counterpart in the output


def classify_pair(tok, out: str) -> str:
    if out == tok.text:
        return IDENTICAL
    if tok.maskable:
        if out == tok.masked_form:
            return MASK_EXACT
        if MASK in out and not any(ch.isalnum() for ch in out):
            return MASK_NONCONFORMING
    return ALTERED


def strict_check(doc, output: str, ignore_trailing_ws: bool = False) -> dict:
    """Line-by-line structural check against the allowed transformations."""
    counts = Counter()
    items = []

    def add(kind, line, detail):
        counts[kind] += 1
        if len(items) < MAX_REPORTED:
            items.append({"type": kind, "line": line, "detail": detail})

    if "\r" in output:
        add("carriage_return_present", 0, f"{output.count(chr(13))} CR")
    out_lines = split_lines(output)
    src_lines = doc.retained
    if len(out_lines) != len(src_lines):
        add(
            "line_count_mismatch",
            0,
            f"expected {len(src_lines)}, got {len(out_lines)}",
        )
    for n, line in enumerate(out_lines, 1):
        if is_blank(line):
            add("blank_line_present", n, "empty or whitespace-only line")
    for n in range(min(len(out_lines), len(src_lines))):
        src = src_lines[n]
        s_text, o_text = src.text, out_lines[n]
        if ignore_trailing_ws:
            s_text, o_text = s_text.rstrip(), o_text.rstrip()
        s_toks = doc.line_tokens[src.retained_no]
        s_seps = TOKEN_RE.split(s_text)
        o_toks = TOKEN_RE.findall(o_text)
        o_seps = TOKEN_RE.split(o_text)
        line_no = n + 1
        if len(o_toks) != len(s_toks):
            add(
                "word_count_mismatch",
                line_no,
                f"expected {len(s_toks)} words, got {len(o_toks)}",
            )
            continue
        if o_seps != s_seps:
            if o_seps[:-1] == s_seps[:-1]:
                add(
                    "trailing_whitespace_mismatch",
                    line_no,
                    f"expected {s_seps[-1]!r}, got {o_seps[-1]!r}",
                )
            else:
                add("whitespace_mismatch", line_no, "spacing differs")
        for tok, out in zip(s_toks, o_toks):
            state = classify_pair(tok, out)
            if state == MASK_NONCONFORMING:
                add(
                    "nonconforming_mask",
                    line_no,
                    f"{tok.comp_id}: expected {tok.masked_form!r}, "
                    f"got {out!r}",
                )
            elif state == ALTERED:
                kind = "partial_mask" if MASK in out else "word_altered"
                add(kind, line_no, f"{tok.comp_id}: got {out[:40]!r}")
    return {
        "pass": not counts,
        "ignore_trailing_whitespace": ignore_trailing_ws,
        "expected_line_count": len(src_lines),
        "output_line_count": len(out_lines),
        "violation_counts": dict(counts),
        "violations": items,
        "violations_truncated": sum(counts.values()) > len(items),
    }


def _dp_align(src, out):
    """Minimum-cost monotonic alignment with a count of optimal solutions.

    Operations: pair (cost 0 when allowed, 1 when the word was altered),
    delete a source word (1), insert an output word (1). Inside a gap all
    deletions precede insertions, so each alignment has one path and the
    path count equals the number of distinct optimal alignments.
    """
    n, m = len(src), len(out)
    width = m + 1
    size = (n + 1) * width
    cost = [[INF] * size for _ in range(3)]  # 0 pair, 1 delete, 2 insert
    ways = [[0] * size for _ in range(3)]
    kind = [None] * size  # pair classification per cell
    cost[0][0], ways[0][0] = 0, 1

    def best(cell, states):
        c = min(cost[s][cell] for s in states)
        w = sum(ways[s][cell] for s in states if cost[s][cell] == c)
        return c, min(w, COUNT_CAP)

    for i in range(n + 1):
        row = i * width
        for j in range(m + 1):
            cell = row + j
            if i and j:
                state = classify_pair(src[i - 1], out[j - 1])
                kind[cell] = state
                c, w = best(cell - width - 1, (0, 1, 2))
                if c < INF:
                    cost[0][cell] = c + (1 if state == ALTERED else 0)
                    ways[0][cell] = w
            if i:
                c, w = best(cell - width, (0, 1))
                if c < INF:
                    cost[1][cell], ways[1][cell] = c + 1, w
            if j:
                c, w = best(cell - 1, (0, 1, 2))
                if c < INF:
                    cost[2][cell], ways[2][cell] = c + 1, w
    end = size - 1
    total, n_opt = best(end, (0, 1, 2))
    if n_opt != 1:
        return total, n_opt, None, None

    states = [None] * n
    inserted = []
    i, j = n, m
    cur = min((0, 1, 2), key=lambda s: cost[s][i * width + j])
    while i or j:
        cell = i * width + j
        here = cost[cur][cell]
        if cur == 0:
            states[i - 1] = kind[cell]
            step = 1 if kind[cell] == ALTERED else 0
            prev, allowed = cell - width - 1, (0, 1, 2)
            i, j = i - 1, j - 1
        elif cur == 1:
            states[i - 1] = DELETED
            step, prev, allowed = 1, cell - width, (0, 1)
            i -= 1
        else:
            inserted.append({"output_index": j - 1, "text": out[j - 1][:40]})
            step, prev, allowed = 1, cell - 1, (0, 1, 2)
            j -= 1
        cur = next(s for s in allowed if cost[s][prev] == here - step)
    inserted.reverse()
    return total, 1, states, inserted


def align(doc, output: str) -> dict:
    """Align output words to source words; never guesses positions."""
    src = doc.tokens
    out = TOKEN_RE.findall(output)
    n, m = len(src), len(out)
    base = {"source_words": n, "output_words": m}
    if n == m:
        states = [classify_pair(t, o) for t, o in zip(src, out)]
        if ALTERED not in states:
            return {
                **base,
                "status": "ALIGNED",
                "evaluable": True,
                "cost": 0,
                "optimal_alignments": 1,
                "states": states,
                "inserted": [],
            }
    if m > 4 * n + 50:
        return {
            **base,
            "status": "UNALIGNABLE",
            "evaluable": False,
            "reason": "output has far more words than the source",
            "states": None,
            "inserted": None,
        }
    total, n_opt, states, inserted = _dp_align(src, out)
    if states is None:
        return {
            **base,
            "status": "UNALIGNABLE",
            "evaluable": False,
            "cost": total,
            "optimal_alignments": f">={n_opt}" if n_opt else "0",
            "reason": "more than one optimal alignment",
            "states": None,
            "inserted": None,
        }
    gaps = bool(inserted) or DELETED in states
    return {
        **base,
        "status": "ALIGNED_WITH_GAPS" if gaps else "ALIGNED_WITH_ALTERED",
        "evaluable": not gaps,
        "cost": total,
        "optimal_alignments": 1,
        "states": states,
        "inserted": inserted,
    }


def masked_ids(doc, states) -> set:
    """Components hidden in the output (exact or non-conforming mask)."""
    return {
        tok.comp_id
        for tok, st in zip(doc.tokens, states)
        if st in (MASK_EXACT, MASK_NONCONFORMING)
    }


def anchor_check(doc, output: str, anchor_lines) -> dict:
    """The brief shows the first lines of a correct output, unmasked."""
    k = len(anchor_lines)
    src_head = [ln.text.rstrip() for ln in doc.retained[:k]]
    if src_head != list(anchor_lines):
        return {"applicable": False, "pass": None}
    out_head = [ln.rstrip() for ln in split_lines(output)[:k]]
    return {
        "applicable": True,
        "pass": out_head == list(anchor_lines),
        "note": "compared with trailing whitespace ignored",
    }


def fence_check(doc, output: str) -> dict:
    """Markdown fences added by the model (source fences are content)."""
    src_fences = sum(
        1 for ln in doc.retained if ln.text.lstrip().startswith("```")
    )
    out_fences = sum(
        1 for ln in split_lines(output) if ln.lstrip().startswith("```")
    )
    return {
        "source_fence_lines": src_fences,
        "output_fence_lines": out_fences,
        "added": out_fences > src_fences,
    }


def summarize(validation: dict) -> dict:
    """Compact view of a validation report for the result contract."""
    return {
        "structural_pass": validation["structural_pass"],
        "pass_ignoring_trailing_whitespace": validation[
            "pass_ignoring_trailing_whitespace"
        ],
        "violation_counts": validation["strict"]["violation_counts"],
        "expected_line_count": validation["strict"]["expected_line_count"],
        "output_line_count": validation["strict"]["output_line_count"],
        "alignment_status": validation["alignment"]["status"],
        "alignment_evaluable": validation["alignment"]["evaluable"],
        "brief_anchor_lines_pass": validation["brief_anchor_lines"]["pass"],
        "markdown_fence_added": validation["markdown_fences"]["added"],
        "semantic_completeness": "NOT ASSESSED by structural validation",
    }


def validate_candidate(doc, output: str, policy) -> dict:
    """Full structural validation of a model-written candidate."""
    strict = strict_check(doc, output)
    relaxed = strict_check(doc, output, ignore_trailing_ws=True)
    alignment = align(doc, output)
    anchors = anchor_check(doc, output, policy.anchor_lines)
    fences = fence_check(doc, output)
    state_counts = (
        dict(Counter(alignment["states"])) if alignment["states"] else None
    )
    structural_pass = (
        strict["pass"]
        and not fences["added"]
        and anchors["pass"] is not False
    )
    return {
        "structural_pass": structural_pass,
        "strict": strict,
        "pass_ignoring_trailing_whitespace": relaxed["pass"]
        and not fences["added"]
        and anchors["pass"] is not False,
        "relaxed_violation_counts": relaxed["violation_counts"],
        "alignment": {
            k: v for k, v in alignment.items() if k != "states"
        },
        "alignment_state_counts": state_counts,
        "alignment_states": "".join(alignment["states"])
        if alignment["states"]
        else None,
        "brief_anchor_lines": anchors,
        "markdown_fences": fences,
        "disclaimer": "Structural validity is not evidence that every "
        "personal value was masked or that nothing was over-masked.",
    }
