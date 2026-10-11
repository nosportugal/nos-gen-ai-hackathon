"""Score saved runs against the provisional reference.

Usage (workspace root, inside the virtual environment):

    python -I evaluation/evaluate_runs.py --index runs/_benchmarks/ID.json

Reads each run's saved candidate, recomputes the alignment, and writes a
per-trial CSV plus a Markdown file with per-trial and aggregate tables.
This is shared evaluation code; no agent imports it and no agent sees
the reference.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation import metrics  # noqa: E402
from shared import config  # noqa: E402
from shared.policy import load_policy  # noqa: E402
from shared.validation import align, strict_check  # noqa: E402

REFERENCE = config.ROOT / "evaluation" / "reference_annotations.json"
REFERENCE_STATUS = "PROVISIONAL (AI-drafted, not human-reviewed)"
NA = "N/A"

COLUMNS = [
    "benchmark_id", "agent", "trial", "mode", "run_id", "status",
    "failure_reason", "eligibility", "model_id", "model_version",
    "calls_submitted", "http_attempts", "prompt_tokens", "output_tokens",
    "thoughts_tokens", "total_tokens", "cost", "model_latency_s",
    "render_latency_s", "pipeline_latency_s", "candidate_exists",
    "structural_pass", "ledger_agreement_pass",
    "pass_ignoring_trailing_ws",
    "whitespace_line_violations", "alignment_status", "evaluable",
    "ref_mask_n", "ref_keep_n", "ref_ambiguous_n_excluded",
    "ambiguous_hidden_n", "tp", "fp", "fn", "tn", "precision", "recall",
    "f1", "exact_agreement", "over_masking_rate", "under_masking_rate",
    "ref_mask_entities", "entity_full_mask_rate", "char_inserted",
    "char_deleted", "char_substituted", "exact_reference_match",
    "lines_equal_reference", "reference_status",
]
WS_KINDS = ("line_count_mismatch", "blank_line_present",
            "whitespace_mismatch", "trailing_whitespace_mismatch",
            "word_count_mismatch", "carriage_return_present")


def fmt(value):
    if value is None:
        return NA
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4f}"
    return value


def score_run(entry: dict, doc, reference, bench_id: str):
    """Return (csv row, alignment states or None)."""
    row = {key: NA for key in COLUMNS}
    row.update({
        "benchmark_id": bench_id, "agent": entry["agent"],
        "trial": entry["trial"], "reference_status": REFERENCE_STATUS,
    })
    result_path = entry.get("result")
    if not result_path:
        row["mode"] = entry.get("mode", NA)
        row["status"] = entry.get("status", "NOT_RUN")
        row["failure_reason"] = entry.get("failure_reason", NA)
        row["candidate_exists"] = "no"
        return row, None
    result = config.load_json(config.ROOT / result_path)
    usage, timings = result["usage"], result["timings"]
    versions = {s["model_version"] for s in result["stages"]
                if s["model_version"]}
    row.update({
        "mode": result["mode"], "run_id": result["run_id"],
        "status": result["status"],
        "failure_reason": result["failure_reason"] or "",
        "eligibility": result["competition_eligibility"]["status"],
        "model_id": result["model"]["id"],
        "model_version": "/".join(sorted(versions)) or "UNKNOWN",
        "calls_submitted": usage["calls_submitted"],
        "http_attempts": usage["http_attempts"],
        "prompt_tokens": usage["prompt_tokens"],
        "output_tokens": usage["output_tokens"],
        "thoughts_tokens": usage["thoughts_tokens"],
        "total_tokens": usage["total_tokens"], "cost": usage["cost"],
        "model_latency_s": timings["model_s"],
        "render_latency_s": timings["render_s"],
        "pipeline_latency_s": timings["pipeline_s"],
    })
    cand_path = result["artifacts"].get("candidate")
    row["candidate_exists"] = "yes" if cand_path else "no"
    if not cand_path:
        return row, None
    candidate = config.read_text_exact(config.ROOT / cand_path)
    strict = strict_check(doc, candidate)
    relaxed = strict_check(doc, candidate, ignore_trailing_ws=True)
    alignment = align(doc, candidate)
    states = alignment["states"]
    checks = result.get("validation") or {}
    row.update({
        "structural_pass": fmt(strict["pass"]),
        "ledger_agreement_pass": fmt(checks.get("ledger_agreement_pass")),
        "pass_ignoring_trailing_ws": fmt(relaxed["pass"]),
        "whitespace_line_violations": sum(
            strict["violation_counts"].get(k, 0) for k in WS_KINDS
        ),
        "alignment_status": alignment["status"],
        "evaluable": fmt(alignment["evaluable"]),
    })
    acc = (metrics.accuracy(doc, reference, states)
           if alignment["evaluable"] else metrics.empty_accuracy())
    for key, value in acc.items():
        row[key] = fmt(value)
    for key, value in metrics.fidelity(doc, candidate, states).items():
        row[key] = fmt(value)
    agree = metrics.reference_agreement(doc, reference, candidate)
    row["exact_reference_match"] = fmt(agree["exact_reference_match"])
    row["lines_equal_reference"] = (
        f"{agree['lines_equal_reference']}/{agree['reference_lines']}"
    )
    return row, states if alignment["evaluable"] else None


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def aggregate(rows, states_by_agent) -> list:
    out = []
    for agent in sorted({r["agent"] for r in rows}):
        mine = [r for r in rows if r["agent"] == agent]
        ran = [r for r in mine if r["run_id"] != NA]
        valid = [r for r in ran if r["status"] == "CANDIDATE_VALID"]
        scored = [r for r in ran if r["evaluable"] == "yes"]

        def avg(key):
            vals = [float(r[key]) for r in scored if r[key] != NA]
            return mean(vals)

        def total(key):
            vals = [r[key] for r in ran]
            if not vals or any(not isinstance(v, int) for v in vals):
                return "UNKNOWN" if ran else NA
            return sum(vals)

        dis = metrics.disagreement(states_by_agent.get(agent, []))
        out.append({
            "agent": agent,
            "trials_planned": len(mine),
            "trials_run": len(ran),
            "pipeline_failures": sum(
                1 for r in ran if r["status"] == "PIPELINE_FAILED"
            ),
            "candidates_produced": sum(
                1 for r in ran if r["candidate_exists"] == "yes"
            ),
            "valid_candidates": len(valid),
            "overall_valid_output_rate": fmt(
                metrics.ratio(len(valid), len(mine)) if ran else None
            ),
            "evaluable_outputs": len(scored),
            "mean_precision_evaluable": fmt(avg("precision")),
            "mean_recall_evaluable": fmt(avg("recall")),
            "mean_f1_evaluable": fmt(avg("f1")),
            "mean_exact_agreement_evaluable": fmt(avg("exact_agreement")),
            "mean_over_masking_evaluable": fmt(avg("over_masking_rate")),
            "mean_under_masking_evaluable": fmt(avg("under_masking_rate")),
            "calls_submitted_total": total("calls_submitted"),
            "http_attempts_total": total("http_attempts"),
            "prompt_tokens_total": total("prompt_tokens"),
            "output_tokens_total": total("output_tokens"),
            "mean_model_latency_s": fmt(mean(
                [float(r["model_latency_s"]) for r in ran]
            )),
            "mean_pipeline_latency_s": fmt(mean(
                [float(r["pipeline_latency_s"]) for r in ran]
            )),
            "repeat_pairs_compared": dis["pairs_compared"],
            "max_words_differing_between_repeats": fmt(
                dis["max_words_differing"]
            ),
        })
    return out


def md_table(rows, columns) -> str:
    head = "| " + " | ".join(columns) + " |"
    rule = "|" + "|".join("---" for _ in columns) + "|"
    body = ["| " + " | ".join(str(r[c]) for c in columns) + " |"
            for r in rows]
    return "\n".join([head, rule] + body)


def evaluate(index: dict, out_csv: Path, out_md: Path) -> dict:
    policy = load_policy()
    doc = policy.make_doc(config.read_text_exact(config.CANONICAL_SOURCE))
    reference = config.load_json(REFERENCE)
    if reference["meta"]["source_sha256"] != config.sha256_text(doc.text):
        raise SystemExit("reference was built for a different source")
    rows, states_by_agent = [], {}
    for entry in index["runs"]:
        row, states = score_run(entry, doc, reference, index["benchmark_id"])
        rows.append(row)
        if states is not None:
            states_by_agent.setdefault(entry["agent"], []).append(states)
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    agg = aggregate(rows, states_by_agent)
    label = index["mode"]
    if index.get("blocked"):
        note = ("BLOCKED before any request was sent: "
                f"{index['blocked']} No Gemini call was made; every row "
                "is a NOT_RUN placeholder, not a result.")
    elif label == "MOCK":
        note = ("MOCK run: these rows exercise the code path only and "
                "are NOT Gemini results.")
    else:
        note = "LIVE Gemini run."
    statuses = Counter(r["status"] for r in rows)
    per_trial_cols = [
        "agent", "trial", "status", "structural_pass",
        "pass_ignoring_trailing_ws", "alignment_status", "tp", "fp", "fn",
        "precision", "recall", "f1", "exact_agreement",
        "over_masking_rate", "under_masking_rate", "ambiguous_hidden_n",
        "char_inserted", "char_deleted", "char_substituted",
        "exact_reference_match", "calls_submitted", "prompt_tokens",
        "output_tokens", "model_latency_s", "pipeline_latency_s",
    ]
    text = "\n".join([
        f"# Benchmark tables - {index['benchmark_id']}",
        "",
        f"- Mode: {label}. {note}",
        f"- Reference status: {REFERENCE_STATUS}. Every accuracy figure "
        "below is PROVISIONAL.",
        f"- Planned trials: {len(rows)}; statuses: {dict(statuses)}.",
        "- N/A marks an undefined value; UNKNOWN marks usage the backend "
        "did not report. Neither is zero.",
        "",
        "## Per-trial results",
        "",
        md_table(rows, per_trial_cols),
        "",
        "## Aggregates per agent",
        "",
        md_table(agg, list(agg[0])) if agg else "(no rows)",
        "",
    ])
    config.write_text_exact(out_md, text)
    return {"rows": rows, "aggregates": agg}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--index", required=True)
    parser.add_argument("--out-csv")
    parser.add_argument("--out-md")
    args = parser.parse_args(argv)
    index = config.load_json(args.index)
    stem = "benchmark" if index["mode"] == "LIVE" else "mock_benchmark"
    base = config.ROOT / "evaluation"
    out_csv = Path(args.out_csv or base / f"{stem}_results.csv")
    out_md = Path(args.out_md or base / f"{stem}_tables.md")
    evaluate(index, out_csv, out_md)
    print("written:", config.rel(out_csv), config.rel(out_md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
