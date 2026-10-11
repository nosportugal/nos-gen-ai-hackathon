"""Run an agent (model + prompt) over the dataset and score every answer.

One run is one model + one prompt + one dataset file. Each run is saved
as runs/<sweep>/<doc>.json, where a sweep is one call of this script, and
the model's answer, exactly as returned, as runs/<sweep>/<doc>.txt:

    {"provider", "model", "prompt", "prompt_sha256", "document",
     "seconds", "usage", "error",
     "syntax": {"valid": ..., "problems": [...]},
     "counts": {"tp", "fp", "fn", "tn"},
     "metrics": {"precision", "recall", "f1", "accuracy",
                 "specificity", "fpr", "fnr"},
     "false_positives": [{"id": "L3:W2", "text": "..."}],
     "false_negatives": [...],
     "unaligned": [...]}

A positive is a word the ground truth masks. Words come from mask_diff,
so only words with something to mask are counted. A word the answer
breaks the rules at (masked is null) is counted as not masked and also
listed under "unaligned". runs/<sweep>/summary.json adds up all runs.

Usage (from submission/):
    python -m benchmark.scorer --prompt prompts/prompt_v3_2.txt
    python -m benchmark.scorer --provider local --limit 5
    python -m benchmark.scorer --docs doc_001 doc_007
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from agent.llm import (
    DEFAULT_LOCAL_URL,
    DEFAULT_MODELS,
    TIMEOUT_S,
    answer_text,
    api_key,
    get_llm,
    to_messages,
)
from agent.prompt import DEFAULT_PROMPT, build_messages, load_prompt

from .mask_diff import mask_diff
from .mask_syntax_validation import read, validate

BENCHMARK = Path(__file__).resolve().parent
DATASET = BENCHMARK
RUNS = BENCHMARK / "runs"


def ratio(a, b):
    return a / b if b else None


def metrics(c: dict) -> dict:
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    return {
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
        "accuracy": ratio(tp + tn, tp + fp + fn + tn),
        "specificity": ratio(tn, tn + fp),
        "fpr": ratio(fp, fp + tn),
        "fnr": ratio(fn, fn + tp),
    }


def score(source: str, answer: str, truth: str) -> dict:
    """Compare the words the answer masked with the ground truth."""
    expected = mask_diff(source, truth)
    got = mask_diff(source, answer)
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    lists = {"false_positives": [], "false_negatives": [], "unaligned": []}
    for wid, word in expected.items():
        if word["masked"] is None:
            continue  # the ground truth itself breaks the rules here
        item = {"id": wid, "text": word["text"]}
        masked = got[wid]["masked"]
        if masked is None:
            lists["unaligned"].append(item)
        if word["masked"] and masked:
            counts["tp"] += 1
        elif word["masked"]:
            counts["fn"] += 1
            lists["false_negatives"].append(item)
        elif masked:
            counts["fp"] += 1
            lists["false_positives"].append(item)
        else:
            counts["tn"] += 1
    return {"counts": counts, "metrics": metrics(counts), **lists}


def run_one(llm, system: str, source: str, truth: str) -> tuple:
    """Ask the model to mask one document; return (score, answer)."""
    start = time.monotonic()
    try:
        reply = llm.invoke(to_messages(*build_messages(system, source)))
        answer = answer_text(reply)
    except Exception as exc:  # API, network or incomplete answer
        error = f"{type(exc).__name__}: {exc}"
        key = api_key()
        return {"seconds": round(time.monotonic() - start, 1),
                "error": error.replace(key, "[KEY]") if key else error}, None
    result = {
        "seconds": round(time.monotonic() - start, 1),
        "usage": getattr(reply, "usage_metadata", None),
        "error": None,
        "syntax": validate(source, answer),
    }
    result.update(score(source, answer, truth))
    return result, answer


def documents(dataset: Path, names=None, limit=None) -> list:
    paths = sorted((dataset / "input").glob("*.txt"))
    if names:
        paths = [p for p in paths if p.stem in names]
    return paths[:limit]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", choices=DEFAULT_MODELS,
                        default=os.environ.get("LLM_PROVIDER", "gemini"))
    parser.add_argument("--model", help="model name (default per provider)")
    parser.add_argument("--base-url", default=DEFAULT_LOCAL_URL,
                        help="URL of the local OpenAI-compatible server")
    parser.add_argument("--timeout", type=float, default=TIMEOUT_S,
                        help=f"seconds per model call (default {TIMEOUT_S})")
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--dataset", type=Path, default=DATASET,
                        help="folder with input/ and ground_truth/")
    parser.add_argument("--docs", nargs="+", metavar="NAME",
                        help="only these documents, e.g. doc_001")
    parser.add_argument("--limit", type=int, help="only the first N")
    parser.add_argument("--runs", type=Path, default=RUNS)
    args = parser.parse_args(argv)
    model = args.model or DEFAULT_MODELS[args.provider]

    try:
        system = load_prompt(args.prompt)
        llm = get_llm(args.provider, model, args.base_url,
                      args.timeout)
    except ValueError as exc:
        print(exc)
        return 2
    paths = documents(args.dataset, args.docs, args.limit)
    if not paths:
        print(f"no documents in {args.dataset / 'input'}")
        return 2

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = re.sub(r"[^\w.-]+", "-", f"{stamp}_{model}_{args.prompt.stem}")
    out_dir = args.runs / name
    out_dir.mkdir(parents=True)
    about = {
        "provider": args.provider, "model": model,
        "prompt": str(args.prompt),
        "prompt_sha256": hashlib.sha256(system.encode()).hexdigest(),
    }
    total = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    failed = valid = 0
    for path in paths:
        # REVIEW: exact reads preserve CRLF, but validate() rejects CR.
        # Windows references pass only after LF normalisation.
        # Agree on the line-ending contract before using syntax results.
        # See README.md: "Review required: benchmark line endings".
        source = read(path)
        truth = read(args.dataset / "ground_truth" / path.name)
        result, answer = run_one(llm, system, source, truth)
        if answer is not None:
            (out_dir / path.name).write_bytes(answer.encode("utf-8"))
        run = {**about, "document": path.name, **result}
        (out_dir / f"{path.stem}.json").write_text(
            json.dumps(run, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        if result["error"]:
            failed += 1
            print(f"{path.stem}  FAILED: {result['error']}")
            continue
        valid += result["syntax"]["valid"]
        for k in total:
            total[k] += result["counts"][k]
        syntax = "ok " if result["syntax"]["valid"] else "BAD"
        f1 = result["metrics"]["f1"]
        f1 = "-" if f1 is None else round(f1, 3)
        c = result["counts"]
        print(f"{path.stem}  syntax {syntax}  f1 {f1}"
              f"  fp {c['fp']}  fn {c['fn']}")

    summary = {**about, "documents": len(paths), "failed": failed,
               "syntax_valid": valid, "counts": total,
               "metrics": metrics(total)}
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(summary["metrics"], indent=2))
    print(f"wrote {out_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
